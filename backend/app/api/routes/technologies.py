from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.learning import TechnologyUnits
from app.services import learning_catalog

# Public, read-only. Technology-level links between Home, Dev and Career (P2).
router = APIRouter(prefix="/api/technologies", tags=["technologies"])


@router.get("/{technology_slug}/units", response_model=TechnologyUnits)
def list_technology_units(
    technology_slug: str = Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64),
    db: Session = Depends(get_db),
) -> TechnologyUnits:
    return learning_catalog.get_technology_units(db, technology_slug)
