"""Read-only queries over the public career roles. Only published roles are visible,
in their fixed file order: no user, learner type or setting changes the answer."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.career import CareerRole, CareerRoleTechnology
from app.models.content import Technology
from app.schemas.career import (
    CareerRoleDetail,
    CareerRoleList,
    CareerRoleSummary,
    RoleReference,
    RoleTechnology,
)
from app.schemas.content import TechnologyRef
from app.services.learning_catalog import units_by_technology

PUBLISHED = "published"


class CareerRoleNotFound(AppError):
    status_code = 404
    code = "CAREER_ROLE_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("Career role not found")


def published_role(db: Session, slug: str) -> CareerRole:
    role = db.scalar(
        select(CareerRole).where(CareerRole.slug == slug, CareerRole.status == PUBLISHED)
    )
    if role is None:
        raise CareerRoleNotFound()
    return role


def _role_technologies(db: Session, role_ids: list[int]):
    """(role_id, importance, technology) rows for published technologies, in order."""
    return db.execute(
        select(CareerRoleTechnology.role_id, CareerRoleTechnology.importance, Technology)
        .join(Technology, Technology.id == CareerRoleTechnology.technology_id)
        .where(CareerRoleTechnology.role_id.in_(role_ids), Technology.status == PUBLISHED)
        # "core" sorts before "related".
        .order_by(CareerRoleTechnology.importance, CareerRoleTechnology.position)
    ).all()


def list_roles(db: Session) -> CareerRoleList:
    roles = list(
        db.scalars(
            select(CareerRole)
            .where(CareerRole.status == PUBLISHED)
            .order_by(CareerRole.position, CareerRole.id)
        )
    )
    core: dict[int, list[TechnologyRef]] = {role.id: [] for role in roles}
    counts: dict[int, int] = {role.id: 0 for role in roles}
    for role_id, importance, technology in _role_technologies(db, list(core)):
        counts[role_id] += 1
        if importance == "core":
            core[role_id].append(TechnologyRef(slug=technology.slug, name=technology.name))
    return CareerRoleList(
        items=[
            CareerRoleSummary(
                slug=role.slug,
                name=role.name,
                summary=role.summary,
                core_technologies=core[role.id],
                technology_count=counts[role.id],
            )
            for role in roles
        ]
    )


def get_role(db: Session, slug: str) -> CareerRoleDetail:
    role = published_role(db, slug)
    links = _role_technologies(db, [role.id])
    units = units_by_technology(db, [technology.id for _, _, technology in links])
    return CareerRoleDetail(
        slug=role.slug,
        name=role.name,
        summary=role.summary,
        description_md=role.description_md,
        tasks=list(role.tasks),
        references=[RoleReference(**ref) for ref in role.reference_links],
        technologies=[
            RoleTechnology(
                slug=technology.slug,
                name=technology.name,
                importance=importance,
                units=units[technology.id],
            )
            for _, importance, technology in links
        ],
    )
