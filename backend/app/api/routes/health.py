import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.errors import AppError

logger = logging.getLogger("devhub.health")

router = APIRouter(prefix="/api/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    database: str


@router.get("", response_model=HealthResponse)
def liveness() -> HealthResponse:
    """The process is up. Does not touch the database."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadinessResponse)
def readiness(db: Session = Depends(get_db)) -> ReadinessResponse:
    """The app can reach its database."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("Database readiness check failed: %s", type(exc).__name__)
        raise AppError(
            "Database is unavailable", code="DATABASE_UNAVAILABLE", status_code=503
        ) from exc
    return ReadinessResponse(status="ok", database="ok")
