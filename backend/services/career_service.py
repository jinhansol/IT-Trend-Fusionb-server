# backend/services/career_service.py
# flake8: noqa

import json
from collections import Counter
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database.mariadb import SessionLocal
from database.models import CareerJob, UserProfile


# ==========================================
# 🔎 인식할 기술 키워드 (직무 추출용)
# ==========================================
TECH_KEYWORDS = [
    "Python", "React", "Node", "TypeScript", "Vue",
    "Next.js", "Java", "Spring", "Django", "Flutter",
    "AWS", "Kubernetes", "Docker", "AI", "ML", "Data",
]


# ==========================================
# 🧩 제목에서 기술 스킬 추출
# ==========================================
def extract_skills_from_title(title: str):
    found = []
    if not title:
        return found

    lower_title = title.lower()
    for skill in TECH_KEYWORDS:
        if skill.lower() in lower_title:
            found.append(skill)

    return found


# ==========================================
# 📊 8주간 기술 트렌드 분석
# ==========================================
def get_weekly_tech_trends(db: Session, weeks: int = 8):
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=weeks)

    jobs = (
        db.query(CareerJob)
        .filter(CareerJob.posted_date >= start_date)
        .all()
    )

    weekly_counter = Counter()

    for job in jobs:
        skills = extract_skills_from_title(job.title)
        weekly_counter.update(skills)

    trend_list = [
        {"skill": skill, "count": count}
        for skill, count in weekly_counter.most_common()
    ]

    return trend_list


# ==========================================
# 🎯 사용자 관심 기술 가져오기
# ==========================================
def get_user_skills(user: UserProfile):
    if not user:
        return []

    raw = user.tech_stack

    # JSON 리스트일 경우
    if isinstance(raw, list):
        return [s for s in raw if isinstance(s, str) and s.strip()]

    # 문자열일 경우: "Python, React"
    if isinstance(raw, str):
        return [s.strip() for s in raw.split(",") if s.strip()]

    return []


# ==========================================
# 🎯 사용자 맞춤 채용 추천
# ==========================================
def get_recommended_jobs(db: Session, skills: list, limit: int = 20):
    if not skills:
        return (
            db.query(CareerJob)
            .order_by(CareerJob.posted_date.desc())
            .limit(limit)
            .all()
        )

    query = db.query(CareerJob)
    filters = []

    for skill in skills:
        if skill:
            filters.append(CareerJob.title.ilike(f"%{skill}%"))

    if filters:
        query = query.filter(*filters)

    return (
        query.order_by(CareerJob.posted_date.desc())
        .limit(limit)
        .all()
    )


# =================================================
# 💾 DB 저장 로직 — 크롤링한 데이터를 CareerJob에 저장
# =================================================
def save_job_posting(db: Session, job_data: dict):
    """
    크롤링 결과(dict)를 CareerJob 테이블에 저장하는 함수.
    하드코딩 없음. 목업 없음.
    job_data 예:
    {
        'title': 'Python 개발자',
        'company': '삼성전자',
        'location': '서울 강남구',
        'tags': ['Python', 'AI'],
        'url': 'https://www.jobkorea.co.kr/...',
        'source': 'JobKorea'
    }
    """

    # 1) URL 기준 중복 체크
    exists = (
        db.query(CareerJob)
        .filter(CareerJob.url == job_data["url"])
        .first()
    )

    if exists:
        return False  # 이미 저장됨

    job = CareerJob(
        title=job_data.get("title"),
        company=job_data.get("company"),
        location=job_data.get("location"),
        tags=json.dumps(job_data.get("tags", []), ensure_ascii=False),
        url=job_data.get("url"),
        source=job_data.get("source", "Unknown"),
        posted_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )

    try:
        db.add(job)
        db.commit()
        return True
    except:
        db.rollback()
        return False


# =================================================
# 💾 크롤링 결과 리스트를 CareerJob 테이블에 저장하는 Pipeline
# =================================================
def save_crawled_jobs(results: list[dict]):
    """
    JobKorea / 사람인 / 기타 크롤러에서 가져온 데이터(dict 리스트)를
    CareerJob 테이블에 일괄 저장하는 pipeline.
    """
    db = SessionLocal()
    saved = 0

    for job in results:
        ok = save_job_posting(db, job)
        if ok:
            saved += 1

    db.close()
    print(f"💾 CareerJob 저장 완료: {saved}개 / 총 {len(results)}개")


# ======================
# 사용 예시 (크롤링 파일에서 호출)
# ======================
"""
from services.jobkorea_crawler import crawl_jobkorea
from services.career_service import save_crawled_jobs

results = crawl_jobkorea("Python")
save_crawled_jobs(results)
"""
