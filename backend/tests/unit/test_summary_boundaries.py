"""E1 boundaries, checked from the source: the summary code stays offline and apart.

- app.summaries never reaches the network (no HTTP client, sockets or the collector's
  fetcher), so no article page can be requested before SSRF/DNS checks exist.
- The web app and the collector never import the summary code or the LLM interface:
  no model call can happen in a request or during collection. The one job that may
  call a model are the translation and summary jobs (app/jobs/translate.py,
  app/jobs/summarize.py), each run on its own.
- Gemini (google.genai) is reached only through app/integrations/gemini.py, and only the
  job command line (app/jobs/__main__.py) builds that client or starts those jobs.
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
        "google",
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
    assert users == {
        "summaries/summarizer.py",
        "summaries/translate.py",
        "jobs/translate.py",
        "jobs/summarize.py",
        "integrations/gemini.py",
    }


def test_web_app_and_collector_do_not_import_summaries():
    jobs = {
        APP / "jobs" / "translate.py",
        APP / "jobs" / "summarize.py",
        APP / "jobs" / "__main__.py",
        APP / "integrations" / "gemini.py",
    }
    outside = [p for p in APP.rglob("*.py") if SUMMARIES not in p.parents and p not in jobs]
    offenders = {
        str(path.relative_to(APP))
        for path in outside
        if any(matches(n, ["app.summaries", "app.integrations.llm"]) for n in imports(path))
    }
    assert offenders == set()


def test_only_the_job_command_line_imports_the_model_jobs():
    users = {
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if any(matches(n, ["app.jobs.translate", "app.jobs.summarize"]) for n in imports(path))
    }
    assert users == {"jobs/__main__.py"}


def test_only_the_job_command_line_builds_the_gemini_client():
    sdk = {
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if any(matches(n, ["google"]) for n in imports(path))
    }
    users = {
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if any(matches(n, ["app.integrations.gemini"]) for n in imports(path))
    }
    assert sdk == {"integrations/gemini.py"}
    assert users == {"jobs/__main__.py"}
