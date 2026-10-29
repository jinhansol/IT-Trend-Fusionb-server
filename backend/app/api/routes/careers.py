from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.career import CareerRoleDetail, CareerRoleList
from app.services import career_catalog

# Public, read-only career exploration (P3). Saving candidates and goals is under /api/me.
router = APIRouter(prefix="/api/careers", tags=["careers"])


@router.get("/roles", response_model=CareerRoleList)
def list_roles(db: Session = Depends(get_db)) -> CareerRoleList:
    return career_catalog.list_roles(db)


@router.get("/roles/{role_slug}", response_model=CareerRoleDetail)
def get_role(
    role_slug: str = Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64),
    db: Session = Depends(get_db),
) -> CareerRoleDetail:
    return career_catalog.get_role(db, role_slug)
