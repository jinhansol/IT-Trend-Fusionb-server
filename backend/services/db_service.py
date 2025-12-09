# services/db_service.py
from sqlalchemy.orm import Session
from sqlalchemy import exists
from datetime import datetime

from database.models import NewsFeed, CareerJob


# =======================================================
# 📰 NEWS FEED 저장 및 조회
# =======================================================
def save_news_feed(db: Session, news_list: list):
    """크롤링된 뉴스 저장 (중복 방지)"""
    try:
        added_count = 0

        for n in news_list:
            title = n.get("title")
            if not title:
                continue

            exists_query = db.query(
                exists().where(NewsFeed.title == title)
            ).scalar()

            if exists_query:
                continue

            db_news = NewsFeed(
                title=title,
                summary=n.get("summary"),
                content=n.get("content"),
                category=n.get("category"),
                keywords=n.get("keywords"),
                source=n.get("source"),
                url=n.get("url"),
                published_at=n.get("published_at"),
                created_at=datetime.utcnow(),
            )
            db.add(db_news)
            added_count += 1

        db.commit()
        print(f"[DB] NewsFeed {added_count}개 저장 완료")
    except Exception as e:
        db.rollback()
        print(f"[DB] News 저장 실패: {e}")


def get_latest_news(db: Session, limit: int = 8):
    """홈 화면 최신 뉴스"""
    try:
        return (
            db.query(NewsFeed)
            .order_by(NewsFeed.published_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as e:
        print(f"[DB] 뉴스 조회 오류: {e}")
        return []
