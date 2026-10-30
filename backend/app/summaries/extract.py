"""Article HTML or Markdown -> limited Markdown for the summarizer, plus an omissions report.

Kept: headings (as #), paragraphs, lists, fenced code with its language, tables,
notes/warnings (as "> **주의:**") and image alt text. Dropped: scripts, styles,
navigation, forms, embeds, comment/share/related boxes, and every link target (the
link text stays), so nothing from the page can become a URL in the output.

Size caps cut code lines and table rows first, then the body of later sections.
Headings always stay, so the outline of the article survives. Every cut is counted
in Omissions; the summarizer marks such input as partial or refuses it.
Nothing here touches the network or stores the text.
"""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

CODE_LINES = 40
TABLE_ROWS = 10
TABLE_COLS = 6

_SKIP_TAGS = {
    "head",
    "script",
    "style",
    "noscript",
    "template",
    "iframe",
    "object",
    "embed",
    "svg",
    "canvas",
    "nav",
    "header",
    "footer",
    "form",
    "button",
    "select",
}
_SKIP_CLASSES = re.compile(r"\b(comments?|related|share|sharing|advert\w*|ads?|newsletter)\b")
_NOTE_CLASSES = re.compile(r"\b(note|warning|caution|callout|admonition|tip|alert|important)\b")
_VOID = {"area", "base", "br", "col", "hr", "img", "input", "link", "meta", "source", "wbr"}
_BLOCKS = {"p", "div", "section", "article", "main", "li", "dd", "dt", "figure", "figcaption"}
_LANGUAGE = re.compile(r"(?:language|lang)-([\w+#.-]+)")
_SPACES = re.compile(r"[ \t\r\f\v]+")
_NOTE_LABEL = re.compile(r"^\**\s*(주의|경고|참고|note|warning|caution|tip)\s*\**\s*[:：]\s*", re.I)


@dataclass
class Block:
    kind: str  # heading | text | list | code | table | note | image
    text: str = ""
    level: int = 0
    items: list[str] = field(default_factory=list)
    ordered: bool = False
    language: str | None = None
    lines: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class Omissions:
    chars_before: int = 0
    chars_after: int = 0
    headings_total: int = 0
    sections_total: int = 0
    sections_truncated: int = 0
    sections_dropped: int = 0  # body fully removed (the heading stays)
    code_blocks_total: int = 0
    code_lines_total: int = 0
    code_lines_kept: int = 0
    tables_total: int = 0
    table_rows_total: int = 0
    table_rows_kept: int = 0

    @property
    def body_cut_ratio(self) -> float:
        return 0.0 if not self.chars_before else 1 - self.chars_after / self.chars_before

    @property
    def code_cut_ratio(self) -> float:
        return (
            0.0 if not self.code_lines_total else 1 - self.code_lines_kept / self.code_lines_total
        )


@dataclass
class Extracted:
    text: str
    omissions: Omissions
    code_languages: list[str]
    paragraphs: int  # text, list and note blocks in the output


# --- HTML ---------------------------------------------------------------------------------


def _clean(text: str) -> str:
    return _SPACES.sub(" ", text).strip()


class _HtmlBlocks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self._skip_depth = 0
        self._buffer: list[str] = []
        self._heading: int | None = None
        self._note_depth = 0  # >0 while inside a note element
        self._note_tags: list[str] = []
        self._pre: dict | None = None  # {"language": str | None, "text": [str]}
        self._lists: list[dict] = []  # each {"ordered": bool, "items": [str]}
        self._table: dict | None = None  # {"rows": [[str]], "row": [str] | None}
        self._cell: list[str] | None = None
        self._inline_code = False

    # helpers
    def _flush(self) -> None:
        text = _clean("".join(self._buffer))
        self._buffer = []
        if not text:
            return
        if self._lists:
            self._lists[-1]["items"].append(("  " * (len(self._lists) - 1)) + text)
        elif self._note_depth:
            self.blocks.append(Block("note", text=text))
        else:
            self.blocks.append(Block("text", text=text))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").lower()
        if self._skip_depth:
            if tag not in _VOID:
                self._skip_depth += 1
            return
        is_note = tag == "blockquote" or (
            tag in ("div", "aside", "section", "p") and _NOTE_CLASSES.search(classes)
        )
        if tag in _SKIP_TAGS or (tag == "aside" and not is_note) or _SKIP_CLASSES.search(classes):
            if tag not in _VOID:
                self._skip_depth = 1
            return
        if self._pre is not None:
            if tag == "code" and self._pre["language"] is None:
                match = _LANGUAGE.search(classes)
                self._pre["language"] = match.group(1) if match else None
            return
        if tag == "pre":
            self._flush()
            match = _LANGUAGE.search(classes)
            self._pre = {"language": match.group(1) if match else None, "text": []}
        elif re.fullmatch(r"h[1-6]", tag):
            self._flush()
            self._heading = min(int(tag[1]), 4)
        elif is_note:
            self._flush()
            self._note_depth += 1
            self._note_tags.append(tag)
        elif tag in ("ul", "ol"):
            self._flush()
            self._lists.append({"ordered": tag == "ol", "items": []})
        elif tag == "table":
            self._flush()
            self._table = {"rows": [], "row": None}
        elif tag == "tr" and self._table is not None:
            self._table["row"] = []
        elif tag in ("td", "th") and self._table is not None:
            self._cell = []
        elif tag == "img":
            alt = _clean(attrs.get("alt") or "")
            if alt and self._table is None:
                self._flush()
                self.blocks.append(Block("image", text=f"[이미지: {alt}]"))
        elif tag == "br":
            self._data("\n")
        elif tag == "code":
            self._inline_code = True
            self._data("`")
        elif tag in _BLOCKS:
            self._flush()

    def handle_endtag(self, tag):
        if self._skip_depth:
            self._skip_depth -= 1
            return
        if self._pre is not None:
            if tag == "pre":
                code = "".join(self._pre["text"]).strip("\n")
                lines = code.split("\n") if code else []
                self.blocks.append(Block("code", language=self._pre["language"], lines=lines))
                self._pre = None
            return
        if self._heading is not None and re.fullmatch(r"h[1-6]", tag):
            text = _clean("".join(self._buffer))
            self._buffer = []
            if text:
                self.blocks.append(Block("heading", text=text, level=self._heading))
            self._heading = None
        elif self._note_tags and tag == self._note_tags[-1]:
            self._flush()
            self._note_tags.pop()
            self._note_depth -= 1
        elif tag in ("ul", "ol") and self._lists:
            self._flush()
            done = self._lists.pop()
            if self._lists:  # nested list: its items belong to the outer list
                self._lists[-1]["items"].extend(done["items"])
            elif done["items"]:
                self.blocks.append(Block("list", items=done["items"], ordered=done["ordered"]))
        elif tag in ("td", "th") and self._cell is not None and self._table is not None:
            if self._table["row"] is not None:
                self._table["row"].append(_clean("".join(self._cell)).replace("|", "\\|"))
            self._cell = None
        elif tag == "tr" and self._table is not None:
            if self._table["row"]:
                self._table["rows"].append(self._table["row"])
            self._table["row"] = None
        elif tag == "table" and self._table is not None:
            if self._table["rows"]:
                self.blocks.append(Block("table", rows=self._table["rows"]))
            self._table = None
        elif tag == "code" and self._inline_code:
            self._data("`")
            self._inline_code = False
        elif tag in _BLOCKS:
            self._flush()

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._pre is not None:
            self._pre["text"].append(data)
        else:
            self._data(data)

    def _data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)
        else:
            self._buffer.append(data)

    def close(self):
        super().close()
        if self._pre is not None:  # a page that ends inside <pre> keeps its code
            self.handle_endtag("pre")
        self._flush()


def html_blocks(html: str) -> list[Block]:
    parser = _HtmlBlocks()
    parser.feed(html)
    parser.close()
    return parser.blocks


# --- Markdown -----------------------------------------------------------------------------

_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MD_HTML = re.compile(r"<[^>]+>")
_MD_LIST = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
_MD_TABLE_RULE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")


def _md_inline(text: str) -> str:
    text = _MD_IMAGE.sub(lambda m: f"[이미지: {m.group(1)}]" if m.group(1) else "", text)
    text = _MD_LINK.sub(r"\1", text)
    return _clean(_MD_HTML.sub(" ", text))


def markdown_blocks(markdown: str) -> list[Block]:
    blocks: list[Block] = []
    lines = markdown.replace("\r\n", "\n").split("\n")
    paragraph: list[str] = []

    def flush():
        text = _md_inline(" ".join(paragraph))
        paragraph.clear()
        if text:
            blocks.append(Block("text", text=text))

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush()
            fence, language = stripped[:3], stripped[3:].strip().split(" ")[0] or None
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                code.append(lines[i])
                i += 1
            blocks.append(Block("code", language=language, lines=code))
        elif re.match(r"^#{1,6}\s", stripped):
            flush()
            hashes = len(stripped) - len(stripped.lstrip("#"))
            blocks.append(
                Block("heading", text=_md_inline(stripped[hashes:]), level=min(hashes, 4))
            )
        elif stripped.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                if not _MD_TABLE_RULE.match(row):
                    cells = [_md_inline(c) for c in row.strip("|").split("|")]
                    rows.append(cells)
                i += 1
            blocks.append(Block("table", rows=rows))
            continue
        elif stripped.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            text = _md_inline(" ".join(quote))
            if text:
                blocks.append(Block("note", text=text))
            continue
        elif _MD_LIST.match(line):
            flush()
            items, ordered = [], bool(re.match(r"\s*\d", line))
            while i < len(lines) and (match := _MD_LIST.match(lines[i])):
                indent = "  " * (len(match.group(1)) // 2)
                items.append(indent + _md_inline(match.group(3)))
                i += 1
            blocks.append(Block("list", items=items, ordered=ordered))
            continue
        elif not stripped:
            flush()
        else:
            paragraph.append(stripped)
        i += 1
    flush()
    return blocks


# --- rendering with caps ------------------------------------------------------------------


def _render_block(block: Block) -> str:
    if block.kind == "heading":
        return f"{'#' * block.level} {block.text}"
    if block.kind == "text":
        return block.text
    if block.kind == "note":
        return f"> **주의:** {_NOTE_LABEL.sub('', block.text)}"
    if block.kind == "image":
        return block.text
    if block.kind == "list":
        lines, number = [], 0
        for item in block.items:
            body = item.lstrip(" ")  # nested items carry their indent
            indent = item[: len(item) - len(body)]
            if block.ordered and not indent:  # only top-level items are numbered
                number += 1
                lines.append(f"{number}. {body}")
            else:
                lines.append(f"{indent}- {body}")
        return "\n".join(lines)
    if block.kind == "code":
        return "\n".join([f"```{block.language or ''}", *block.lines, "```"])
    if block.kind == "table":
        header, *rest = block.rows
        lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        lines += ["| " + " | ".join(row) + " |" for row in rest]
        return "\n".join(lines)
    raise ValueError(block.kind)


def _cap_block(block: Block, om: Omissions) -> Block:
    if block.kind == "code":
        om.code_blocks_total += 1
        om.code_lines_total += len(block.lines)
        kept = block.lines[:CODE_LINES]
        om.code_lines_kept += len(kept)
        if len(block.lines) > CODE_LINES:
            kept = [*kept, f"… ({len(block.lines) - CODE_LINES}줄 생략)"]
        return Block("code", language=block.language, lines=kept)
    if block.kind == "table" and block.rows:
        om.tables_total += 1
        body = block.rows[1:]
        om.table_rows_total += len(body)
        kept_rows = body[:TABLE_ROWS]
        om.table_rows_kept += len(kept_rows)
        width = min(TABLE_COLS, max(len(r) for r in block.rows))
        rows = [(r + [""] * width)[:width] for r in [block.rows[0], *kept_rows]]
        if len(body) > TABLE_ROWS:
            rows.append([f"… ({len(body) - TABLE_ROWS}행 생략)"] + [""] * (width - 1))
        return Block("table", rows=rows)
    return block


def render(blocks: list[Block], max_chars: int) -> Extracted:
    om = Omissions()
    capped = [_cap_block(b, om) for b in blocks if b.kind != "table" or b.rows]
    om.chars_before = sum(len(_render_block(b)) for b in blocks if b.kind != "heading")

    # Sections: [heading or None, [body blocks]]
    sections: list[tuple[Block | None, list[Block]]] = []
    for block in capped:
        if block.kind == "heading":
            sections.append((block, []))
        elif sections:
            sections[-1][1].append(block)
        else:
            sections.append((None, [block]))
    om.headings_total = sum(1 for heading, _ in sections if heading is not None)
    om.sections_total = len(sections)

    def total() -> int:
        parts = [_render_block(b) for h, body in sections for b in ([h] if h else []) + body]
        return len("\n\n".join(parts))

    marker = Block("text", text="… (섹션 뒷부분 생략)")
    for index in range(len(sections) - 1, -1, -1):
        if total() <= max_chars:
            break
        heading, body = sections[index]
        if not body:
            continue
        # Drop blocks from the end until the rest, with the marker, fits.
        while body:
            body.pop()
            body.append(marker)
            if total() <= max_chars:
                break
            body.pop()
        if any(b is not marker for b in body):
            om.sections_truncated += 1
        else:
            om.sections_dropped += 1
            body[:] = [marker]

    rendered = [b for h, body in sections for b in ([h] if h else []) + body]
    text = "\n\n".join(_render_block(b) for b in rendered)
    if len(text) > max_chars:  # only headings left and still too long
        text = text[:max_chars].rstrip() + "\n… (생략)"
    om.chars_after = sum(
        len(_render_block(b)) for b in rendered if b.kind != "heading" and b is not marker
    )
    languages = sorted({b.language for b in blocks if b.kind == "code" and b.language})
    paragraphs = sum(1 for b in rendered if b.kind in ("text", "list", "note") and b is not marker)
    return Extracted(text=text, omissions=om, code_languages=languages, paragraphs=paragraphs)


def extract_html(html: str, max_chars: int) -> Extracted:
    return render(html_blocks(html), max_chars)


def extract_markdown(markdown: str, max_chars: int) -> Extracted:
    return render(markdown_blocks(markdown), max_chars)
