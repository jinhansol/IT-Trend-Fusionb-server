# backend/schemas/roadmap_schema.py
# flake8: noqa

from pydantic import BaseModel
from typing import List, Optional

# -----------------------------------------------------------
# ⭐ 1. 퀘스트 정보를 담을 작은 스키마 정의 (RoadmapNode 위쪽에 추가)
# -----------------------------------------------------------
class NodeQuestInfo(BaseModel):
    quest_id: int
    node_db_id: int
    title: str
    description: str | None = None
    xp: int
    category: str | None = None
    search_keywords: list[str] = []  # 서비스에서 보내주는 경우 대비
    completed: bool
    
    # ⭐ [수정] url 필드 추가 (이게 없어서 null로 떴던 것)
    url: str | None = None 
    resource_link: str | None = None

    class Config:
        orm_mode = True


# -----------------------------------------------------------
# ⭐ 2. RoadmapNode 수정 (quests 필드 추가)
# -----------------------------------------------------------
class RoadmapNode(BaseModel):
    id: str
    db_id: int
    label: str
    description: str | None
    icon: str | None
    position: int | None
    status: str
    xp: int
    prerequisites: list[str]
    resource_link: str | None
    thumbnail: str | None

    # ⭐ [핵심 수정] 여기에 quests 필드 추가!
    # 리스트 형태이며, 기본값은 빈 배열([])입니다.
    quests: list[NodeQuestInfo] = []

    class Config:
        orm_mode = True


class RoadmapResponse(BaseModel):
    track_title: str
    track_desc: str | None
    nodes: list[RoadmapNode]


class NodeCompleteResponse(BaseModel):
    message: str
    status: str