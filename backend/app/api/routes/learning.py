from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.learning import TrackDetail, TrackListResponse, UnitDetail
from app.services import learning_catalog

# Public learning catalog. Personal progress lives under /api/me (Phase 4).
router = APIRouter(prefix="/api/tracks", tags=["learning"])


@router.get("", response_model=TrackListResponse)
def list_tracks(db: Session = Depends(get_db)) -> TrackListResponse:
    return learning_catalog.list_tracks(db)


@router.get("/{track_slug}", response_model=TrackDetail)
def get_track(track_slug: str, db: Session = Depends(get_db)) -> TrackDetail:
    return learning_catalog.get_track(db, track_slug)


@router.get("/{track_slug}/units/{unit_slug}", response_model=UnitDetail)
def get_unit(track_slug: str, unit_slug: str, db: Session = Depends(get_db)) -> UnitDetail:
    return learning_catalog.get_unit(db, track_slug, unit_slug)
