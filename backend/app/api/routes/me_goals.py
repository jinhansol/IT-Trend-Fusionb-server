from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.goals import GoalCreate, GoalList, GoalOut, GoalStatus, GoalUpdate
from app.services import learning_goals

# The user's own learning goals (P3). Works with personalization ON or OFF. The user
# always comes from the access token; goal ids of other users answer 404.
router = APIRouter(prefix="/api/me/goals", tags=["me"])

GoalId = Path(gt=0, le=2**63 - 1)


@router.get("", response_model=GoalList)
def list_goals(
    status: GoalStatus | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalList:
    return learning_goals.list_goals(db, user, status)


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(
    body: GoalCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> GoalOut:
    return learning_goals.create_goal(db, user, body)


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(
    body: GoalUpdate,
    goal_id: int = GoalId,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalOut:
    return learning_goals.update_goal(db, user, goal_id, body)


@router.delete("/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int = GoalId, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    learning_goals.delete_goal(db, user, goal_id)
    return Response(status_code=204)
