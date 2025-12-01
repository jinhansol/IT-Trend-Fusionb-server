# backend/services/dev_service.py
# flake8: noqa

from sqlalchemy.orm import Session
from sqlalchemy import select, desc, or_, func
from datetime import datetime
import traceback
from collections import Counter

# 모델과 스키마는 프로젝트 구조에 맞게 Import 경로 확인해주세요
from database.models import DevPost, UserInterest
from schemas.dev_schema import (
    DevFeedResponse, 
    DevPostResponse, 
    FeedSection,
    TagSearchResponse,
    TopicInsightResponse,
    TopicInsightItem,
    IssueInsightResponse,
    IssueInsightItem
)

# -------------------------------------------------------------
# 🛠️ 스크래퍼 Import (없어도 에러 안 나게 처리)
# -------------------------------------------------------------
try:
    from services.dev_scraper import crawl_okky, crawl_devto
except ImportError:
    print("⚠️ dev_scraper 모듈을 찾을 수 없습니다. 크롤링 기능이 제한됩니다.")
    def crawl_okky(): return []
    def crawl_devto(): return []


# ===========================================================
# Helper Functions (날짜/태그 정리 & 자동 분류)
# ===========================================================
def normalize_datetime(value):
    if not value: return None
    if isinstance(value, datetime): return value
    try: return datetime.fromisoformat(value.replace("Z", ""))
    except: return None

def normalize_tags(value):
    if value is None: return []
    if isinstance(value, list): return value
    if isinstance(value, str): return value.split(",")
    return []

TOPIC_KEYWORDS = {
    "AI / ML": ["ai", "ml", "model", "gpt", "llm", "vector", "러닝", "인공지능", "딥러닝"],
    "Frontend": ["react", "next", "vue", "javascript", "css", "html", "프론트", "웹", "ui", "ux"],
    "Backend": ["fastapi", "django", "spring", "java", "node", "python", "백엔드", "서버", "db", "api"],
    "DevOps": ["docker", "k8s", "kubernetes", "cicd", "aws", "cloud", "배포", "운영", "리눅스"],
    "Cloud": ["aws", "gcp", "azure", "lambda", "클라우드", "ec2"],
}

ISSUE_MAP = {
    "Error & Bug": ["error", "exception", "fail", "crash", "bug", "에러", "오류", "실패", "버그", "문제", "안됨", "안돼요"],
    "Environment": ["install", "setup", "config", "env", "setting", "설치", "설정", "환경", "버전", "호환", "mac", "windows"],
    "Deployment": ["deploy", "build", "release", "ci/cd", "배포", "빌드", "운영"],
    "Performance": ["slow", "performance", "latency", "memory", "cpu", "성능", "속도", "최적화", "메모리", "느림"],
    "Development": ["api", "endpoint", "request", "code", "refactor", "구현", "개발", "코드", "방법", "질문", "공유", "팁", "후기", "추천"],
}

DEFAULT_TOPIC = "Others"
DEFAULT_ISSUE = "General Info"

def classify_topic(text: str):
    text = text.lower()
    for topic, keys in TOPIC_KEYWORDS.items():
        if any(k in text for k in keys):
            return topic
    return DEFAULT_TOPIC

def classify_issue(text: str):
    text = text.lower()
    for issue, keys in ISSUE_MAP.items():
        if any(k in text for k in keys):
            return issue
    return DEFAULT_ISSUE


# ===========================================================
# 🔧 DB 저장 로직
# ===========================================================
def save_posts(db: Session, posts: list):
    inserted, updated = 0, 0
    for p in posts:
        try:
            text = (p.get("title", "") + " " + (p.get("summary") or "")).lower()
            tags_list = normalize_tags(p.get("tags"))
            p["published_at"] = normalize_datetime(p.get("published_at"))

            topic = classify_topic(text)
            issue = classify_issue(text)

            exist = db.execute(
                select(DevPost).where(
                    DevPost.source == p["source"],
                    DevPost.source_id == str(p["source_id"]),
                )
            ).scalar_one_or_none()

            if exist:
                exist.title = p["title"]
                exist.url = p["url"]
                exist.summary = p.get("summary")
                exist.tags = tags_list
                exist.like_count = p.get("like_count", 0)
                exist.comment_count = p.get("comment_count", 0)
                exist.view_count = p.get("view_count", 0)
                exist.crawled_at = datetime.utcnow()
                exist.topic_primary = topic
                exist.issue_primary = issue
                updated += 1
            else:
                new_post = DevPost(
                    source=p["source"],
                    source_id=str(p["source_id"]),
                    title=p["title"],
                    url=p["url"],
                    author=p.get("author"),
                    summary=p.get("summary"),
                    tags=tags_list,
                    like_count=p.get("like_count", 0),
                    comment_count=p.get("comment_count", 0),
                    view_count=p.get("view_count", 0),
                    published_at=p["published_at"],
                    crawled_at=datetime.utcnow(),
                    topic_primary=topic,
                    issue_primary=issue,
                )
                db.add(new_post)
                inserted += 1
        except Exception as e:
            print("❌ Error saving post:", e)
            traceback.print_exc()

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print("❌ DB Commit Error:", e)
    return inserted, updated


# ===========================================================
# 🔥 Source Feed (Helper)
# ===========================================================
def get_source_feed(db: Session, source: str, page: int = 1, size: int = 10):
    offset = (page - 1) * size
    query = (
        select(DevPost)
        .where(DevPost.source == source)
        .order_by(desc(DevPost.published_at))
        .offset(offset)
        .limit(size)
    )
    items = db.execute(query).scalars().all()
    total = db.query(DevPost).filter(DevPost.source == source).count()
    return [DevPostResponse.model_validate(item) for item in items], total


# ===========================================================
# 🔵 Public Feed
# ===========================================================
def build_public_feed(db: Session) -> DevFeedResponse:
    try:
        okky_items, okky_total = get_source_feed(db, "okky", page=1, size=50)
        devto_items, devto_total = get_source_feed(db, "devto", page=1, size=50)

        return DevFeedResponse(
            okky=FeedSection(items=okky_items, total=okky_total),
            devto=FeedSection(items=devto_items, total=devto_total),
            updated_at=datetime.utcnow(),
        )
    except Exception as e:
        print(f"Public Feed Error: {e}")
        return DevFeedResponse(updated_at=datetime.utcnow())


# ===========================================================
# 🟣 Personal Feed (수정된 핵심 로직 ✨)
# ===========================================================
def build_personal_feed(current_user, db: Session) -> DevFeedResponse:
    # 1. 유저 관심사 가져오기 (UserInterest 테이블)
    interests = db.query(UserInterest).filter(UserInterest.user_id == current_user.id).all()
    interest_tags = [i.keyword for i in interests]

    # 2. UserProfile의 tech_stack 컬럼도 확인 (만약 모델에 tech_stack이 있다면)
    if hasattr(current_user, "tech_stack") and current_user.tech_stack:
        # tech_stack이 JSON 리스트라고 가정
        if isinstance(current_user.tech_stack, list):
            interest_tags.extend(current_user.tech_stack)
    
    # 중복 제거
    interest_tags = list(set(interest_tags))

    # 3. 관심사가 하나도 없으면 -> 그냥 Public Feed 반환
    if not interest_tags:
        return build_public_feed(db)

    # 4. 필터 생성 (제목 or 요약에 키워드 포함)
    filters = []
    for tag in interest_tags:
        filters.append(DevPost.title.ilike(f"%{tag}%"))
        filters.append(DevPost.summary.ilike(f"%{tag}%"))
    
    # 5. DB 쿼리 실행 (추천 글 가져오기)
    recommended_items = []
    if filters:
        recommended_items = (
            db.query(DevPost)
            .filter(or_(*filters))
            .order_by(desc(DevPost.published_at))
            .limit(100)  # 최대 100개까지만 추천
            .all()
        )

    # 6. [중요] 가져온 추천 글들을 Source별로 다시 분류하기
    okky_filtered = [item for item in recommended_items if item.source == "okky"]
    devto_filtered = [item for item in recommended_items if item.source == "devto"]

    # 7. Public Feed와 동일한 구조로 반환 (프론트엔드 호환성 유지)
    return DevFeedResponse(
        okky=FeedSection(
            items=[DevPostResponse.model_validate(p) for p in okky_filtered], 
            total=len(okky_filtered)
        ),
        devto=FeedSection(
            items=[DevPostResponse.model_validate(p) for p in devto_filtered], 
            total=len(devto_filtered)
        ),
        interests=interest_tags,
        updated_at=datetime.utcnow(),
    )


# ===========================================================
# 🔍 Tag Search
# ===========================================================
def search_by_tag(db: Session, tag: str, limit=30):
    rows = (
        db.query(DevPost)
        .filter(or_(DevPost.title.ilike(f"%{tag}%"), DevPost.summary.ilike(f"%{tag}%")))
        .order_by(desc(DevPost.published_at))
        .limit(limit)
        .all()
    )
    items = [DevPostResponse.model_validate(r) for r in rows]
    return TagSearchResponse(tag=tag, items=items, total=len(rows))


# ===========================================================
# 🔄 Refresh Logic
# ===========================================================
def refresh_all_sources(db: Session):
    try:
        from services.dev_scraper import crawl_okky, crawl_devto
        print("Refreshing OKKY...")
        save_posts(db, crawl_okky())
        print("Refreshing Dev.to...")
        save_posts(db, crawl_devto())
        return {"ok": True, "message": "Refresh completed"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


# ===========================================================
# 🔥 Insight Logic
# ===========================================================
def build_topic_clusters(db: Session):
    rows = db.query(DevPost.topic_primary, func.count(DevPost.id)).group_by(DevPost.topic_primary).all()
    counter = Counter()
    for t, c in rows:
        topic_name = t if t else DEFAULT_TOPIC
        counter[topic_name] += int(c)
    data = [TopicInsightItem(topic=k, count=v) for k, v in counter.most_common()]
    return TopicInsightResponse(clusters=data)

def build_issue_stats(db: Session):
    rows = db.query(DevPost.issue_primary, func.count(DevPost.id)).group_by(DevPost.issue_primary).all()
    data = [IssueInsightItem(category=i or DEFAULT_ISSUE, count=int(c)) for i, c in rows]
    return IssueInsightResponse(issues={item.category: item.count for item in data})

def collect_all_tags(db: Session):
    items = db.query(DevPost).order_by(desc(DevPost.published_at)).limit(200).all()
    tag_counter = Counter()
    for i in items:
        if i.tags:
            tags_list = i.tags if isinstance(i.tags, list) else str(i.tags).split(",")
            tag_counter.update([t.strip().lower() for t in tags_list if t.strip()])
    return [t for t, c in tag_counter.most_common(30)]