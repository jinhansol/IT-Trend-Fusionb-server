# backend/schemas/quest_schema.py
# flake8: noqa

from pydantic import BaseModel


# -----------------------------------------------------------
# ⭐ Quest 기본 스키마
# -----------------------------------------------------------
class QuestBase(BaseModel):
    id: int
    title: str
    description: str | None = None
    url: str | None = None               # 생활코딩 URL이 없는 경우 대비
    xp: int
    difficulty: str                      # easy / normal / hard
    category: str | None = None                       # html, css, js, node, python 등
    chapter: str | None = None           # roadmap chapter (web-basic, backend 등)
    completed: bool
    last_recommended: str | None = None  # YYYY-MM-DD or None

    class Config:
        orm_mode = True


# -----------------------------------------------------------
# ⭐ 일반 응답 스키마
# -----------------------------------------------------------
class QuestResponse(QuestBase):
    pass


# -----------------------------------------------------------
# ⭐ 퀘스트 완료 응답 스키마
# -----------------------------------------------------------
class QuestCompleteResponse(BaseModel):
    message: str
    quest: QuestResponse                 # 더 정확한 타입 지정
