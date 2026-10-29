from fastapi import APIRouter, Depends, Path, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.career import CandidateList, CandidateOut, CandidateSave
from app.services import career_candidates

# The user's saved career candidates (P3). The user always comes from the access token.
router = APIRouter(prefix="/api/me/career-candidates", tags=["me"])

RoleSlug = Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)


@router.get("", response_model=CandidateList)
def list_candidates(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CandidateList:
    return career_candidates.list_candidates(db, user)


@router.put("/{role_slug}", response_model=CandidateOut)
def save_candidate(
    body: CandidateSave,
    role_slug: str = RoleSlug,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CandidateOut:
    return career_candidates.save_candidate(db, user, role_slug, body.note)


@router.delete("/{role_slug}", status_code=204)
def remove_candidate(
    role_slug: str = RoleSlug,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    career_candidates.remove_candidate(db, user, role_slug)
    return Response(status_code=204)
