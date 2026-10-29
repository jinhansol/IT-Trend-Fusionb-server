from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User, UserSettings
from app.schemas.user import MeResponse, SettingsUpdate, UserPublic, UserSettingsOut

router = APIRouter(prefix="/api/me", tags=["me"])


def _settings_out(settings_row: UserSettings | None) -> UserSettingsOut:
    return UserSettingsOut(
        personalization_enabled=bool(settings_row and settings_row.personalization_enabled),
        learner_type=settings_row.learner_type if settings_row else None,
    )


@router.get("", response_model=MeResponse)
def read_me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        **UserPublic.model_validate(user).model_dump(),
        settings=_settings_out(user.user_settings),
    )


@router.patch("/settings", response_model=UserSettingsOut)
def update_settings(
    body: SettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSettingsOut:
    """Change the caller's own settings. Only the fields sent are changed."""
    with db.begin():
        settings_row = db.get(UserSettings, user.id, with_for_update=True)
        if settings_row is None:  # accounts are created with a row; stay safe anyway
            settings_row = UserSettings(user_id=user.id)
            db.add(settings_row)
        if "learner_type" in body.model_fields_set:
            settings_row.learner_type = body.learner_type
        if "personalization_enabled" in body.model_fields_set:
            settings_row.personalization_enabled = body.personalization_enabled
        db.flush()
        result = _settings_out(settings_row)
    return result
