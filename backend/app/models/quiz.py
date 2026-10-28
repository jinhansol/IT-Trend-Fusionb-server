"""Unit quizzes (shared content) and users' attempts.

A quiz belongs to a unit and is versioned: once anyone has attempted a version,
its questions never change; edits create a new version and retire the old one.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR

from app.db.base import Base
from app.db.types import BigId, UtcDateTime, utc_now

QUIZ_STATUSES = ("published", "retired")
QUESTION_TYPES = ("single", "multiple")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = (
        UniqueConstraint("unit_id", "version"),
        # MariaDB has no partial unique index; this generated column is NULL unless
        # the quiz is published, so each unit has at most one published quiz.
        UniqueConstraint("published_unit_id"),
        CheckConstraint(_in_list("status", QUIZ_STATUSES), name="status_valid"),
        CheckConstraint("pass_score_percent BETWEEN 1 AND 100", name="pass_score_range"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("learning_units.id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    pass_score_percent: Mapped[int] = mapped_column(SmallInteger)
    # SHA-256 of the normalized quiz definition; lets the loader detect edits.
    content_hash: Mapped[str] = mapped_column(CHAR(64))
    published_unit_id: Mapped[int | None] = mapped_column(
        BigId, Computed("IF(status = 'published', unit_id, NULL)", persisted=True)
    )
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)

    questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="quiz", order_by="QuizQuestion.position"
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("quiz_id", "key"),
        UniqueConstraint("quiz_id", "position"),
        CheckConstraint(_in_list("type", QUESTION_TYPES), name="type_valid"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(BigId, ForeignKey("quizzes.id", ondelete="RESTRICT"))
    key: Mapped[str] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20))
    prompt: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    choices: Mapped[list["QuizChoice"]] = relationship(
        back_populates="question", order_by="QuizChoice.position"
    )


class QuizChoice(Base):
    __tablename__ = "quiz_choices"
    __table_args__ = (
        UniqueConstraint("question_id", "key"),
        UniqueConstraint("question_id", "position"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("quiz_questions.id", ondelete="RESTRICT")
    )
    key: Mapped[str] = mapped_column(String(32))
    position: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(Text)
    # Never exposed by public responses.
    is_correct: Mapped[bool] = mapped_column(Boolean)

    question: Mapped[QuizQuestion] = relationship(back_populates="choices")


class QuizAttempt(Base):
    """One graded submission. client_submission_id makes resubmits idempotent."""

    __tablename__ = "quiz_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "client_submission_id"),
        CheckConstraint("score_percent BETWEEN 0 AND 100", name="score_percent_range"),
        CheckConstraint("score BETWEEN 0 AND max_score", name="score_range"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    quiz_id: Mapped[int] = mapped_column(BigId, ForeignKey("quizzes.id", ondelete="RESTRICT"))
    client_submission_id: Mapped[str] = mapped_column(CHAR(36))
    score: Mapped[int] = mapped_column(Integer)
    max_score: Mapped[int] = mapped_column(Integer)
    score_percent: Mapped[int] = mapped_column(SmallInteger)
    passed: Mapped[bool] = mapped_column(Boolean)
    submitted_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)

    answers: Mapped[list["QuizAttemptAnswer"]] = relationship(back_populates="attempt")


class QuizAttemptAnswer(Base):
    __tablename__ = "quiz_attempt_answers"

    attempt_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("quiz_questions.id", ondelete="RESTRICT"), primary_key=True
    )
    choice_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("quiz_choices.id", ondelete="RESTRICT"), primary_key=True
    )

    attempt: Mapped[QuizAttempt] = relationship(back_populates="answers")
