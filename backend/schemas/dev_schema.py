# schemas/dev_schema.py
# flake8: noqa

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# =======================================================
# 🔹 공통 DevPost Response
# =======================================================
class DevPostResponse(BaseModel):
    id: int
    source: str            # okky / devto
    source_id: str
    title: str
    url: str
    author: Optional[str]
    summary: Optional[str]
    tags: List[str]
    like_count: int
    comment_count: int
    view_count: int
    published_at: Optional[datetime]
    crawled_at: Optional[datetime]

    class Config:
        orm_mode = True


# =======================================================
# 🔹 Public Feed Response
# =======================================================
class PublicDevFeedResponse(BaseModel):
    okky: List[DevPostResponse]
    devto: List[DevPostResponse]
    updated_at: datetime


# =======================================================
# 🔹 Personal Feed Response
# =======================================================
class PersonalDevFeedResponse(BaseModel):
    interests: List[str]
    from_okky: List[DevPostResponse]
    from_devto: List[DevPostResponse]
    recommended: List[DevPostResponse]
    updated_at: datetime


# =======================================================
# 🔹 Source별 Feed Response
# =======================================================
class SourceFeedResponse(BaseModel):
    source: str                # okky / devto
    total: int
    items: List[DevPostResponse]


# =======================================================
# 🔹 Tag Search Response
# =======================================================
class TagSearchResponse(BaseModel):
    tag: str
    items: List[DevPostResponse]
    total: int
