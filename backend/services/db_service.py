from sqlalchemy.orm import Session
from sqlalchemy import exists
from database.models import HomeNews, JobPost, DevTrend
from datetime import datetime

# ========================================================
# 🏠 HOME NEWS
# ========================================================
def get_home_news(db: Session, limit: int = 5):
    """홈 뉴스 최신순 조회"""
    try:
        return (
            db.query(HomeNews)
            .order_by(HomeNews.published_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as e:
        print(f"[DB] HomeNews 조회 오류: {e}")
        return []


def save_home_news(db: Session, news_list: list):
    """크롤링된 뉴스 저장 (중복 방지)"""
    try:
        added_count = 0
        for n in news_list:
            title = n.get("title")
            if not title:
                continue

            exists_query = db.query(exists().where(HomeNews.title == title)).scalar()
            if exists_query:
                continue  # 이미 존재 → skip

            db_news = HomeNews(
                title=title,
                summary=n.get("summary"),
                link=n.get("link"),
                published_at=n.get("published_at", datetime.utcnow()),
            )
            db.add(db_news)
            added_count += 1

        db.commit()
        print(f"[DB] HomeNews {added_count}개 저장 완료 ✅")
    except Exception as e:
        db.rollback()
        print(f"[DB] HomeNews 저장 실패 ❌ {e}")


# ========================================================
# 💼 JOB POSTS
# ========================================================
def get_job_posts(db: Session, limit: int = 10):
    """최근 잡 공고 조회"""
    try:
        return (
            db.query(JobPost)
            .order_by(JobPost.created_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as e:
        print(f"[DB] JobPost 조회 오류: {e}")
        return []


def save_job_posts(db: Session, jobs: list):
    """크롤링된 잡 데이터 저장 (중복 방지)"""
    try:
        added_count = 0
        for j in jobs:
            title = j.get("title")
            company = j.get("company")
            if not title or not company:
                continue

            # 제목 + 회사로 중복 판단
            exists_query = (
                db.query(exists().where(JobPost.title == title, JobPost.company == company))
                .scalar()
            )
            if exists_query:
                continue

            db_job = JobPost(
                title=title,
                company=company,
                location=j.get("location"),
                skills=j.get("skills"),
                salary=j.get("salary"),
                link=j.get("link"),
                created_at=datetime.utcnow(),
            )
            db.add(db_job)
            added_count += 1

        db.commit()
        print(f"[DB] JobPost {added_count}개 저장 완료 ✅")
    except Exception as e:
        db.rollback()
        print(f"[DB] JobPost 저장 실패 ❌ {e}")


# ========================================================
# 💻 DEV TRENDS
# ========================================================
def get_dev_trends(db: Session, limit: int = 10):
    """개발 언어 트렌드 조회"""
    try:
        return (
            db.query(DevTrend)
            .order_by(DevTrend.updated_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as e:
        print(f"[DB] DevTrend 조회 오류: {e}")
        return []


def save_dev_trends(db: Session, trends: list):
    """언어별 트렌드 데이터 저장 (중복 방지 + 업데이트 지원)"""
    try:
        updated_count, inserted_count = 0, 0

        for t in trends:
            lang = t.get("language")
            if not lang:
                continue

            existing = db.query(DevTrend).filter(DevTrend.language == lang).first()
            if existing:
                # 업데이트 (usage, growth, stars만 덮어쓰기)
                existing.usage = t.get("usage", existing.usage)
                existing.growth = t.get("growth", existing.growth)
                existing.stars = t.get("stars", existing.stars)
                existing.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                db_trend = DevTrend(
                    language=lang,
                    usage=t.get("usage"),
                    growth=t.get("growth"),
                    stars=t.get("stars"),
                    updated_at=datetime.utcnow(),
                )
                db.add(db_trend)
                inserted_count += 1

        db.commit()
        print(
            f"[DB] DevTrend {inserted_count}개 추가, {updated_count}개 업데이트 완료 ✅"
        )
    except Exception as e:
        db.rollback()
        print(f"[DB] DevTrend 저장 실패 ❌ {e}")
