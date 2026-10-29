"""P4 module boundaries, checked from the source (A-plan v0.2, section 12).

Interests and skills are read and written only by services/personalization.py; it
never touches goals, candidates, learning records, XP, settings or the learner type;
and only its own route uses it (no content or learning service, so no ranking).
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
SERVICE = APP / "services" / "personalization.py"


def imports(path: Path) -> set[str]:
    """Fully qualified names imported by a module, e.g. app.services.personalization."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def modules_importing(name: str) -> set[str]:
    return {
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if any(i == name or i.startswith(f"{name}.") for i in imports(path))
    }


def test_only_the_personalization_service_uses_the_personalization_models():
    for model in ("UserInterest", "UserSkill"):
        assert modules_importing(f"app.models.personalization.{model}") == {
            "models/__init__.py",
            "services/personalization.py",
        }


def test_only_its_own_route_uses_the_personalization_service():
    assert modules_importing("app.services.personalization") == {"api/routes/me_personalization.py"}


def test_the_personalization_service_touches_nothing_else():
    used = imports(SERVICE)
    forbidden = {
        "app.models.goals",
        "app.models.career",
        "app.models.progress",
        "app.models.quiz",
        "app.services.learning_goals",
        "app.services.career_candidates",
        "app.services.learning_progress",
        "app.services.rewards",
        "app.models.user.UserSettings",
    }
    assert {i for i in used if i in forbidden or i.rsplit(".", 1)[0] in forbidden} == set()
    # The learner type is never read for personalization (C-2).
    assert "learner_type" not in SERVICE.read_text(encoding="utf-8")
