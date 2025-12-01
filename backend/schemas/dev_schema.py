# backend/schemas/dev_schema.py
# flake8: noqa

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


# =======================================================
# 🔹 DevPost 공통 Response
# =======================================================
class DevPostResponse(BaseModel):
    id: int
    source: str
    source_id: str
    title: str
    url: str
    author: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = []
    like_count: int = 0
    comment_count: int = 0
    view_count: int = 0
    published_at: Optional[datetime] = None
    crawled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =======================================================
# 🔹 Feed Section
# =======================================================
class FeedSection(BaseModel):
    items: List[DevPostResponse] = []
    total: int = 0


# =======================================================
# 🔹 통합 Feed Response (Public + Personal 모두 커버)
# =======================================================
class DevFeedResponse(BaseModel):
    # 공통 필드 (Public)
    okky: Optional[FeedSection] = None
    devto: Optional[FeedSection] = None
    
    # 개인화 필드 (Personal)
    interests: List[str] = []
    from_okky: List[DevPostResponse] = []
    from_devto: List[DevPostResponse] = []
    recommended: List[DevPostResponse] = []
    
    updated_at: Optional[datetime] = None


# =======================================================
# 🔹 기타 Response들
# =======================================================
class SourceFeedResponse(BaseModel):
    source: str
    total: int
    items: List[DevPostResponse]

class TagSearchResponse(BaseModel):
    tag: str
    items: List[DevPostResponse]
    total: int

class TopicInsightItem(BaseModel):
    topic: str
    count: int

class TopicInsightResponse(BaseModel):
    clusters: List[TopicInsightItem]

class IssueInsightItem(BaseModel):
    category: str
    count: int

class IssueInsightResponse(BaseModel):
    issues: Dict[str, int]