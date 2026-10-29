"""Career roles (jobs) and the technologies they use, managed as a file.

    uv run python -m app.content_loader careers <file.yaml> [--dry-run]

Same rules as the other content files: validated completely first, every technology
slug resolved before anything is written, idempotent upsert by slug, and roles
missing from the file are retired instead of deleted (saved candidates and goals
keep pointing at them). Load technologies first.
"""

from pathlib import Path
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content_loader.loader import LoadReport, _assign
from app.content_loader.schema import (
    ContentError,
    Slug,
    _check_bold,
    _read_yaml,
    _require_unique,
    _Strict,
    _validate,
)
from app.content_loader.taxonomy import Name, _http_url
from app.models.career import CareerRole, CareerRoleTechnology
from app.models.content import Technology

Summary = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Task = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LinkTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ReferenceDef(_Strict):
    title: LinkTitle
    url: str = Field(max_length=2048)

    @field_validator("url")
    @classmethod
    def _url(cls, value: str) -> str:
        return _http_url(value)


class RoleTechnologiesDef(_Strict):
    core: list[Slug] = Field(min_length=1, max_length=10)
    related: list[Slug] = Field(default_factory=list, max_length=15)


class RoleDef(_Strict):
    slug: Slug
    name: Name
    position: int = Field(ge=1)
    summary: Summary
    description_md: str = Field(min_length=1, max_length=5000)
    tasks: list[Task] = Field(min_length=1, max_length=10)
    technologies: RoleTechnologiesDef
    # Where the description comes from. At least one source is required.
    references: list[ReferenceDef] = Field(min_length=1, max_length=10)

    @field_validator("description_md")
    @classmethod
    def _bold_renders(cls, value: str) -> str:
        return _check_bold(value)

    @model_validator(mode="after")
    def _technologies_once(self) -> "RoleDef":
        _require_unique(
            [*self.technologies.core, *self.technologies.related], f"technology in role {self.slug}"
        )
        return self


class CareersFile(_Strict):
    roles: list[RoleDef] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> "CareersFile":
        _require_unique([r.slug for r in self.roles], "role slug")
        _require_unique([r.position for r in self.roles], "role position")
        return self


def read_careers(path: Path) -> CareersFile:
    return _validate(CareersFile, _read_yaml(path), path)


def _role_values(role: RoleDef) -> dict:
    return {
        "name": role.name,
        "summary": role.summary,
        "description_md": role.description_md,
        "tasks": list(role.tasks),
        "reference_links": [ref.model_dump() for ref in role.references],
        "position": role.position,
        "status": "published",
    }


def _technology_ids(db: Session, content: CareersFile) -> dict[str, int]:
    """Resolve every technology slug before anything is written."""
    wanted = {
        slug
        for role in content.roles
        for slug in (*role.technologies.core, *role.technologies.related)
    }
    found = dict(
        db.execute(
            select(Technology.slug, Technology.id).where(
                Technology.slug.in_(wanted), Technology.status == "published"
            )
        ).all()
    )
    missing = sorted(wanted - set(found))
    if missing:
        raise ContentError(
            f"careers reference unknown or retired technologies ({', '.join(missing)}). "
            "Load content/technologies.yaml first."
        )
    return found


def _sync_technologies(
    db: Session, role: CareerRole, role_def: RoleDef, ids: dict[str, int], report: LoadReport
) -> None:
    wanted = {
        ids[slug]: (importance, position)
        for importance, slugs in (
            ("core", role_def.technologies.core),
            ("related", role_def.technologies.related),
        )
        for position, slug in enumerate(slugs, start=1)
    }
    current = {
        link.technology_id: link
        for link in db.scalars(
            select(CareerRoleTechnology).where(CareerRoleTechnology.role_id == role.id)
        )
    }
    changed = False
    for technology_id, link in current.items():
        if technology_id not in wanted:
            db.delete(link)
            changed = True
    for technology_id, (importance, position) in wanted.items():
        link = current.get(technology_id)
        values = {"importance": importance, "position": position}
        if link is None:
            db.add(CareerRoleTechnology(role_id=role.id, technology_id=technology_id, **values))
            changed = True
        elif _assign(link, values):
            changed = True
    if changed and role_def.slug not in report.created:
        report.updated.append(f"{role_def.slug} technologies")


def apply_careers(db: Session, content: CareersFile) -> LoadReport:
    report = LoadReport(track="careers", kind="file")
    technology_ids = _technology_ids(db, content)
    existing = {r.slug: r for r in db.scalars(select(CareerRole))}

    for role_def in content.roles:
        values = _role_values(role_def)
        role = existing.get(role_def.slug)
        if role is None:
            role = CareerRole(slug=role_def.slug, **values)
            db.add(role)
            db.flush()
            report.created.append(role_def.slug)
        elif _assign(role, values):
            report.updated.append(role_def.slug)
        _sync_technologies(db, role, role_def, technology_ids, report)

    listed = {r.slug for r in content.roles}
    for slug, role in existing.items():
        if slug not in listed and role.status != "retired":
            role.status = "retired"
            report.retired.append(slug)
    db.flush()
    return report
