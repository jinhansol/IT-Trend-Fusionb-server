"""E1 boundaries, checked from the source: the summary code stays offline and apart.

- app.summaries never reaches the network (no HTTP client, sockets or the collector's
  fetcher), so no article page can be requested before SSRF/DNS checks exist.
- The web app and the collector never import the summary code or the LLM interface:
  no model call can happen in a request or during collection. The one job that may
  call a model is the translation job (app/jobs/translate.py), run on its own.
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
SUMMARIES = APP / "summaries"


def imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def matches(name: str, prefixes) -> bool:
    return any(name == p or name.startswith(f"{p}.") for p in prefixes)


def test_summary_code_has_no_network_access():
    network = (
        "httpx",
        "requests",
        "urllib.request",
        "http.client",
        "socket",
        "aiohttp",
        "app.integrations.http",
        "app.integrations.sources",  # imports the HTTP fetcher
        "app.jobs",
        "openai",
        "anthropic",
    )
    found = {
        f"{path.name}: {name}"
        for path in SUMMARIES.rglob("*.py")
        for name in imports(path)
        if matches(name, network)
    }
    assert found == set()


def test_only_the_summarizer_and_translator_use_the_llm_interface():
    users = {
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if any(matches(n, ["app.integrations.llm"]) for n in imports(path))
    }
    assert users == {"summaries/summarizer.py", "summaries/translate.py", "jobs/translate.py"}


def test_web_app_and_collector_do_not_import_summaries():
    job = APP / "jobs" / "translate.py"
    outside = [p for p in APP.rglob("*.py") if SUMMARIES not in p.parents and p != job]
    offenders = {
        str(path.relative_to(APP))
        for path in outside
        if any(matches(n, ["app.summaries", "app.integrations.llm"]) for n in imports(path))
    }
    assert offenders == set()


def test_the_collector_and_the_web_app_never_import_the_translation_job():
    users = {
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if any(matches(n, ["app.jobs.translate"]) for n in imports(path))
    }
    assert users == set()
