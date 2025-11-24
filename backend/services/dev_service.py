# services/dev_service.py
# flake8: noqa

"""
🔥 DevDashboard v4 – Service Layer (Tistory 제거 버전)
- OKKY / Dev.to 크롤링
- JSON/DateTime 안정화
- DB upsert
- Public / Personal / Source Feed
"""

from sqlalchemy.orm import Session
from sqlalchemy import select, desc, or_, func
from datetime import datetime
import traceback

from database.models import DevPost, DevUserPreference, UserInterest
from schemas.dev_schema import (
    PublicDevFeedResponse,
    PersonalDevFeedResponse,
    SourceFeedResponse,
    TagSearchResponse,
)

from services.dev_scraper import (
    fetch_okky_latest,
    fetch_devto_latest,
)


# ===========================================================
# Helper – published_at 보정
# ===========================================================
def normalize_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", ""))
    except:
        return None


# ===========================================================
# Helper – tags 보정
# ===========================================================
def normalize_tags(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []


# ===========================================================
# 🔧 DB 저장 함수 (통합)
# ===========================================================
def save_posts(db: Session, posts: list):
    inserted, updated = 0, 0

    for p in posts:
        try:
            p["tags"] = normalize_tags(p.get("tags"))
            p["published_at"] = normalize_datetime(p.get("published_at"))

            exist = db.execute(
                select(DevPost).where(
                    DevPost.source == p["source"],
                    DevPost.source_id == p["source_id"],
                )
            ).scalar_one_or_none()

            if exist:
                exist.title = p["title"]
                exist.url = p["url"]
                exist.author = p.get("author")
                exist.summary = p.get("summary")
                exist.tags = p["tags"]
                exist.like_count = p.get("like_count", 0)
                exist.comment_count = p.get("comment_count", 0)
                exist.view_count = p.get("view_count", 0)
                exist.published_at = p["published_at"]
                exist.crawled_at = datetime.utcnow()
                updated += 1
            else:
                new_post = DevPost(
                    source=p["source"],
                    source_id=p["source_id"],
                    title=p["title"],
                    url=p["url"],
                    author=p.get("author"),
                    summary=p.get("summary"),
                    tags=p["tags"],
                    like_count=p.get("like_count", 0),
                    comment_count=p.get("comment_count", 0),
                    view_count=p.get("view_count", 0),
                    published_at=p["published_at"],
                    crawled_at=datetime.utcnow(),
                )
                db.add(new_post)
                inserted += 1

        except Exception as e:
            print("❌ Error saving post:", e)
            print("Payload:", p)
            traceback.print_exc()

    db.commit()
    return inserted, updated


# ===========================================================
# 🔥 Source별 feed
# ===========================================================
def get_source_feed(db: Session, source: str, limit=20):
    query = (
        select(DevPost)
        .where(DevPost.source == source)
        .order_by(desc(DevPost.published_at), desc(DevPost.crawled_at))
        .limit(limit)
    )
    return db.execute(query).scalars().all()


# ===========================================================
# 🔥 Public feed
# ===========================================================
def build_public_feed(db: Session):
    try:
        okky_data = fetch_okky_latest(limit=20)
        devto_data = fetch_devto_latest(limit=20)

        save_posts(db, okky_data)
        save_posts(db, devto_data)

        okky = get_source_feed(db, "okky")
        devto = get_source_feed(db, "devto")

        return PublicDevFeedResponse(
            okky=okky,
            devto=devto,
            updated_at=datetime.utcnow(),
        )

    except Exception as e:
        print("❌ build_public_feed ERROR:", e)
        traceback.print_exc()
        return PublicDevFeedResponse(
            okky=[],
            devto=[],
            updated_at=datetime.utcnow()
        )


# ===========================================================
# 🔥 Personal feed
# ===========================================================
def build_personal_feed(current_user, db: Session):
    user_id = current_user.id

    interests = (
        db.query(UserInterest)
        .filter(UserInterest.user_id == user_id)
        .order_by(UserInterest.id.desc())
        .all()
    )
    interest_tags = [i.keyword for i in interests]

    if not interest_tags:
        return build_public_feed(db)

    from_okky, from_devto = [], []

    for tag in interest_tags:
        # OKKY
        okky_rows = (
            db.query(DevPost)
            .filter(
                DevPost.source == "okky",
                or_(
                    DevPost.title.ilike(f"%{tag}%"),
                    DevPost.summary.ilike(f"%{tag}%") if DevPost.summary is not None else False,
                ),
            ).all()
        )
        from_okky.extend(okky_rows)

        # Dev.to
        devto_rows = (
            db.query(DevPost)
            .filter(
                DevPost.source == "devto",
                func.json_contains(DevPost.tags, f'"{tag}"'),
            ).all()
        )
        from_devto.extend(devto_rows)

    recommended = list({p.id: p for p in (from_okky + from_devto)}.values())

    recommended = sorted(
        recommended,
        key=lambda x: (x.published_at or datetime.min, x.crawled_at),
        reverse=True,
    )

    return PersonalDevFeedResponse(
        interests=interest_tags,
        from_okky=from_okky,
        from_devto=from_devto,
        recommended=recommended,
        updated_at=datetime.utcnow(),
    )


# ===========================================================
# 🔍 Tag Search
# ===========================================================
def search_by_tag(db: Session, tag: str, limit=30):
    rows = (
        db.query(DevPost)
        .filter(
            or_(
                DevPost.title.ilike(f"%{tag}%"),
                DevPost.summary.ilike(f"%{tag}%") if DevPost.summary is not None else False,
                func.json_contains(DevPost.tags, f'"{tag}"'),
            )
        )
        .order_by(desc(DevPost.published_at), desc(DevPost.crawled_at))
        .limit(limit)
        .all()
    )

    return TagSearchResponse(tag=tag, items=rows, total=len(rows))


# ===========================================================
# 🔄 Refresh (OKKY + DEVTO만)
# ===========================================================
def refresh_all_sources(db: Session):
    okky = fetch_okky_latest(limit=50)
    devto = fetch_devto_latest(limit=50)

    r1 = save_posts(db, okky)
    r2 = save_posts(db, devto)

    return {
        "okky": {"inserted": r1[0], "updated": r1[1]},
        "devto": {"inserted": r2[0], "updated": r2[1]},
    }


# ===========================================================
# 🔥 전체 태그 수집
# ===========================================================
def collect_all_tags(db: Session):
    items = db.query(DevPost).all()
    all_tags = []

    for i in items:
        if i.tags:
            all_tags.extend(i.tags)

    return sorted(list(set(all_tags)))
