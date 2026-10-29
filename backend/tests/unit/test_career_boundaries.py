"""P3 module boundaries, checked from the source (A-plan v0.2, section 12).

Career exploration never writes learning goals or settings; the goal service never
writes candidates, settings, progress or XP. The services that may write a table are
the only ones that import its model.
"""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"

# module -> names it must not import (models of tables it must never write, writers).
FORBIDDEN = {
    "services/career_catalog.py": {"LearningGoal", "UserSettings", "UserCareerCandidate"},
    "services/career_candidates.py": {
        "LearningGoal",
        "UserSettings",
        "UserUnitProgress",
        "XpLedgerEntry",
        "learning_goals",
        "learning_progress",
        "rewards",
    },
    "services/learning_goals.py": {
        "UserCareerCandidate",
        "UserSettings",
        "XpLedgerEntry",
        "UserActivityRecord",
        "career_candidates",
        "learning_progress",
        "rewards",
    },
    "api/routes/careers.py": {"learning_goals", "career_candidates", "LearningGoal"},
    "api/routes/me_careers.py": {"learning_goals", "LearningGoal", "UserSettings"},
    "api/routes/me_goals.py": {"career_candidates", "UserCareerCandidate", "UserSettings"},
    "content_loader/careers.py": {"LearningGoal", "UserCareerCandidate", "UserSettings"},
}


def imported_names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            names.update(part for part in (node.module or "").split("."))
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.update(alias.name.split("."))
    return names


@pytest.mark.parametrize(("module", "forbidden"), sorted(FORBIDDEN.items()))
def test_module_does_not_import_what_it_must_not_write(module, forbidden):
    assert imported_names(APP / module) & forbidden == set()


def test_only_the_goal_service_imports_the_goal_model():
    users = {
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if "LearningGoal" in imported_names(path)
    }
    assert users == {"models/__init__.py", "services/learning_goals.py"}


def test_only_the_settings_route_writes_settings():
    users = {
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if "UserSettings" in imported_names(path)
    }
    # Existing writers only (auth creates the row at sign-up, /api/me/settings edits it).
    assert users == {"models/__init__.py", "api/routes/me.py", "services/auth.py"}
