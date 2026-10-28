from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import MeResponse, UserPublic, UserSettingsOut

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=MeResponse)
def read_me(user: User = Depends(get_current_user)) -> MeResponse:
    settings_row = user.user_settings
    return MeResponse(
        **UserPublic.model_validate(user).model_dump(),
        settings=UserSettingsOut(
            personalization_enabled=bool(settings_row and settings_row.personalization_enabled)
        ),
    )
