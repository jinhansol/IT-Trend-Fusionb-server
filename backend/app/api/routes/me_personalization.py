from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.personalization import InterestsUpdate, PersonalizationOut, SkillsUpdate
from app.services import personalization

# The user's own personalization data (P4). Readable and editable with the switch ON
# or OFF; the switch itself is PATCH /api/me/settings. No recommendations in P4.
router = APIRouter(prefix="/api/me/personalization", tags=["me"])


@router.get("", response_model=PersonalizationOut)
def read_personalization(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PersonalizationOut:
    return personalization.get_personalization(db, user)


@router.put("/interests", response_model=PersonalizationOut)
def replace_interests(
    body: InterestsUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PersonalizationOut:
    return personalization.replace_interests(db, user, body)


@router.put("/skills", response_model=PersonalizationOut)
def replace_skills(
    body: SkillsUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PersonalizationOut:
    return personalization.replace_skills(db, user, body)


@router.post("/reset", status_code=204)
def reset_personalization(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    personalization.reset(db, user)
    return Response(status_code=204)
