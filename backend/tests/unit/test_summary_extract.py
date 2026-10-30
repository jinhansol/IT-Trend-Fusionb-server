"""Extraction on synthetic HTML and Markdown: structure kept, page noise and URLs dropped."""

import re

import pytest

from app.summaries.extract import extract_html, extract_markdown, html_blocks
from app.summaries.policy import MAX_INPUT_CHARS, sufficiency
from tests.summary_helpers import article

URL = re.compile(r"(https?:|javascript:|data:)", re.IGNORECASE)


def test_news_page_keeps_the_article_and_drops_page_noise():
    extracted = extract_html(article("news_ko.html"), MAX_INPUT_CHARS["news"])
    text = extracted.text

    assert text.startswith("# 데브클라우드, 서울 리전에 관리형 벡터 DB 정식 출시")
    assert "1,200개 팀" in text and "12월 31일까지" in text
    assert "[이미지: 벡터스토어 콘솔 화면]" in text
    assert "관련 링크에 대한 설명은 없다." in text  # link text kept, target dropped
    noise_words = ("메뉴 텍스트", "window.track", "공유하기", "댓글", "관련 기사", "무단 전재")
    for noise in (*noise_words, "가상 기사"):
        assert noise not in text
    assert not URL.search(text)
    assert extracted.paragraphs == 5
    assert sufficiency("news", extracted) == "full"


def test_english_news_drops_newsletter_comments_and_scripts():
    text = extract_html(article("news_en.html"), MAX_INPUT_CHARS["news"]).text

    assert "2.1 billion dollars" in text and "450 watts" in text
    for noise in ("newsletter", "reader comment", "tracking pixel", "Home | Tech"):
        assert noise not in text


def test_dev_html_keeps_headings_code_tables_lists_and_warnings():
    extracted = extract_html(article("dev_spring.html"), MAX_INPUT_CHARS["dev"])
    text, om = extracted.text, extracted.omissions

    headings = [line for line in text.split("\n") if line.startswith("#")]
    assert headings == [
        "# Spring Boot 3에서 가상 스레드로 블로킹 I/O 처리량 늘리기 (가상 기술 블로그)",
        "## 설정",
        "### 설정 항목 정리",
        "## 구현",
        "## 한계",
    ]
    assert "```yaml\nspring:\n  threads:\n    virtual:\n      enabled: true\n```" in text
    assert "```java\npublic class OrderService {" in text
    assert "… (22줄 생략)\n```" in text  # 62 lines -> 40 kept
    assert "| 항목 | 값 | 설명 |\n|---|---|---|\n| 설정 0 | 값 0 | 설명 0 |" in text
    assert "| … (2행 생략) |  |  |" in text  # 12 rows -> 10 kept
    assert "1. JDBC 호출을 감싸던 별도 스레드 풀을 제거한다.\n2. synchronized" in text
    assert "> **주의:** synchronized 블록 안에서 블로킹 I/O를 하면" in text
    assert "블로그 홈" not in text and "© 가상 블로그" not in text

    assert extracted.code_languages == ["java", "yaml"]
    assert (om.code_blocks_total, om.code_lines_total, om.code_lines_kept) == (2, 66, 44)
    assert (om.tables_total, om.table_rows_total, om.table_rows_kept) == (1, 12, 10)
    assert om.sections_truncated == om.sections_dropped == 0


def test_dev_markdown_keeps_fences_inline_code_lists_and_notes():
    extracted = extract_markdown(article("dev_python.md"), MAX_INPUT_CHARS["dev"])
    text = extracted.text

    assert text.count("```python") == 2
    assert "async with asyncio.TaskGroup() as group:" in text  # code kept verbatim
    assert "`asyncio.gather`" in text
    assert "- `CancelledError`를 잡았다면 반드시 다시 던진다." in text
    note = "> **주의:** `CancelledError`를 잡고 다시 던지지 않으면"
    assert note in text  # the article's own "주의:" is not doubled
    assert extracted.code_languages == ["python"]
    assert sufficiency("dev", extracted) == "full"


def test_size_cap_cuts_later_sections_but_keeps_every_heading():
    extracted = extract_html(article("dev_spring.html"), 900)
    text, om = extracted.text, extracted.omissions

    for heading in ("# Spring Boot 3", "## 설정", "### 설정 항목 정리", "## 구현", "## 한계"):
        assert heading in text
    assert "… (섹션 뒷부분 생략)" in text
    assert om.sections_dropped + om.sections_truncated >= 1
    assert om.chars_after < om.chars_before
    assert sufficiency("dev", extracted) == "insufficient"  # sections lost entirely


def test_partial_input_is_flagged_not_refused():
    paragraph = "가상 스레드 설정과 커넥션 풀 조정에 관한 설명 문단이다. " * 8
    md = "# 제목\n\n" + "\n\n".join([paragraph] * 4) + "\n\n## 마지막 절\n\n"
    md += "\n\n".join([paragraph] * 5)
    full = extract_markdown(md, 100_000)
    # Room for everything except the last paragraph of the last section.
    cut = extract_markdown(md, len(full.text) - len(paragraph.strip()) + 10)

    assert cut.omissions.sections_truncated == 1 and cut.omissions.sections_dropped == 0
    assert cut.text.endswith("… (섹션 뒷부분 생략)")
    assert sufficiency("dev", cut) == "partial"


def test_short_content_is_insufficient():
    extracted = extract_html(article("short.html"), MAX_INPUT_CHARS["news"])
    assert sufficiency("news", extracted) == "insufficient"


@pytest.mark.parametrize(
    "html",
    [
        "<p>unclosed <b>bold <i>italic",
        "<div><p>a</div></p></span>",
        "<<<>>> not really html &amp; &bogus; &#x0;",
        "<script>never closed",
        "",
    ],
)
def test_broken_html_never_raises(html):
    extract_html(html, 1000)


def test_attributes_events_and_link_targets_never_reach_the_text():
    html = (
        '<p onclick="steal()">Click <a href="javascript:alert(1)">here</a> and '
        '<a href="data:text/html;base64,AAAA">there</a>.</p>'
        '<img src="x" onerror="alert(1)" alt="diagram">'
        "<table><tr><th>a|b</th></tr><tr><td>c</td></tr></table>"
    )
    text = extract_html(html, 1000).text

    assert text.startswith("Click here and there.")
    assert "[이미지: diagram]" in text
    assert "| a\\|b |" in text  # a pipe inside a cell cannot break the table
    assert not URL.search(text) and "steal" not in text and "onerror" not in text


def test_nested_skipped_elements_end_at_the_right_tag():
    blocks = html_blocks("<nav><div><ul><li>menu</li></ul></div><img src=x></nav><p>body text</p>")
    assert [(b.kind, b.text) for b in blocks] == [("text", "body text")]


def test_markdown_links_images_and_raw_html_become_plain_text():
    md = "See [the docs](https://example.com/docs) ![chart](https://img/x.png) <b>now</b>."
    text = extract_markdown(md, 1000).text
    assert text == "See the docs [이미지: chart] now ."


def test_a_section_left_with_only_the_marker_counts_as_dropped():
    md = "# A\n\n" + "첫 절 문단. " * 30 + "\n\n## B\n\n" + "둘째 절 문단. " * 30
    full = extract_markdown(md, 100_000)
    cut = extract_markdown(md, len(full.text.split("\n\n## B")[0]) + 40)

    assert (cut.omissions.sections_dropped, cut.omissions.sections_truncated) == (1, 0)
    assert cut.text.endswith("## B\n\n… (섹션 뒷부분 생략)")


def test_a_page_ending_inside_pre_keeps_its_code():
    extracted = extract_html("<p>intro</p><pre><code class='language-go'>func main() {\n}", 1000)
    assert extracted.text == "intro\n\n```go\nfunc main() {\n}\n```"
    assert extracted.code_languages == ["go"]


def test_nested_items_do_not_shift_the_numbering_of_an_ordered_list():
    html = "<ol><li><p>one</p><ul><li>a</li><li>b</li></ul></li><li>two</li></ol>"
    assert extract_html(html, 1000).text == "1. one\n  - a\n  - b\n2. two"


def test_code_inside_headings_and_table_cells_is_kept():
    html = (
        "<h2>Use <code>TaskGroup</code></h2>"
        "<table><tr><th>k</th></tr><tr><td><code>x|y</code></td></tr></table>"
    )
    assert extract_html(html, 1000).text == "## Use `TaskGroup`\n\n| k |\n|---|\n| `x\\|y` |"
