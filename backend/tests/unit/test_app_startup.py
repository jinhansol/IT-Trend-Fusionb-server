"""Importing and building the app must not touch the network, the database or threads."""

import subprocess
import sys

from tests.conftest import BACKEND_DIR, TEST_JWT_SECRET, UNIT_DATABASE_URL

PROBE = f"""
import socket, threading

def _forbidden(*args, **kwargs):
    raise RuntimeError("network access during import/app creation")

socket.socket.connect = _forbidden
socket.socket.connect_ex = _forbidden
socket.create_connection = _forbidden

threads_before = threading.active_count()

import app.main
import app.api.routes.health
import app.core.config, app.core.errors, app.core.logging
import app.db.base, app.db.safety, app.db.session, app.models
import app.core.security, app.services.auth, app.api.routes.auth, app.api.routes.me
import app.api.routes.learning, app.services.learning_catalog, app.content_loader.loader
import app.api.routes.me_learning, app.services.learning_progress, app.services.rewards
import app.api.routes.content, app.services.content_feed, app.services.tagging
import app.content_loader.taxonomy, app.jobs.runner, app.jobs.store, app.jobs.__main__
import app.integrations.http, app.integrations.sources
import app.api.routes.careers, app.api.routes.me_careers, app.api.routes.me_goals
import app.services.career_catalog, app.services.career_candidates, app.services.learning_goals
import app.services.transactions, app.content_loader.careers
from app.core.config import Settings

settings = Settings(
    _env_file=None,
    app_env="local",
    database_url={UNIT_DATABASE_URL!r},
    jwt_secret={TEST_JWT_SECRET!r},
)
application = app.main.create_app(settings)

assert threading.active_count() == threads_before, "app creation started a thread"
assert application.state.engine.pool.checkedout() == 0
print("OK")
"""


def test_import_and_create_app_have_no_side_effects():
    result = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("OK")


def test_new_app_does_not_import_legacy_modules():
    """The new app must not pull in the legacy backend (routers/, services/, database/...)."""
    probe = (
        "import sys, app.main\n"
        "legacy = {'main', 'database', 'routers', 'services', 'core', 'scheduler', 'schemas'}\n"
        "loaded = sorted(m for m in sys.modules if m.split('.')[0] in legacy)\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], cwd=BACKEND_DIR, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr


def test_web_app_does_not_load_the_collector():
    """Collector-only code and libraries stay out of the web process."""
    probe = (
        "import sys, app.main\n"
        "loaded = sorted(m for m in sys.modules\n"
        "                if m.split('.')[0] in {'feedparser', 'httpx'}\n"
        "                or m.startswith(('app.jobs', 'app.integrations')))\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], cwd=BACKEND_DIR, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr


def test_new_app_never_calls_create_all():
    offenders = [
        str(path.relative_to(BACKEND_DIR))
        for folder in ("app", "alembic")
        for path in (BACKEND_DIR / folder).rglob("*.py")
        if "create_all(" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
