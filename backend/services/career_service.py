# backend/services/career_service.py
# flake8: noqa

from collections import Counter
from datetime import datetime, timedelta
from typing import List, Optional, Any

from sqlalchemy.orm import Session

from database.mariadb import SessionLocal
from database.models import CareerJob, UserProfile


###########################################
# 🔎 기술 키워드 리스트
###########################################
TECH_KEYWORDS = [
    "Python", "React", "Node", "TypeScript", "Vue",
    "Next.js", "Java", "Spring", "Django", "Flutter",
    "AWS", "Kubernetes", "Docker", "AI", "ML", "Data",
]


###########################################
# 🧩 제목 기반 기술 추출
###########################################
def extract_skills_from_title(title: Optional[str]) -> List[str]:
    found: List[str] = []
    if not title:
        return found
    lower_title = title.lower()
    for skill in TECH_KEYWORDS:
        if skill.lower() in lower_title:
            found.append(skill)
    return found


###########################################
# 🏷 태그 정규화
###########################################
def normalize_tags(raw_tags: Any, title: Optional[str] = None) -> List[str]:
    tags: List[str] = []

    # 1) 기본 tag 처리
    if isinstance(raw_tags, list):
        for t in raw_tags:
            if isinstance(t, str) and t.strip():
                tags.append(t.strip())

    elif isinstance(raw_tags, str):
        for t in raw_tags.split(","):
            tag = t.strip()
            if tag:
                tags.append(tag)

    # 2) 제목에서 기술 스킬 자동 추출
    if title:
        tags.extend(extract_skills_from_title(title))

    # 3) 소문자 기준 중복 제거
    unique = {}
    for t in tags:
        key = t.lower()
        if key not in unique:
            unique[key] = t

    return list(unique.values())


###########################################
# ⏳ posted_date 파싱
###########################################
def parse_posted_date(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw

    if isinstance(raw, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(raw)
        except Exception:
            pass

    return datetime.utcnow()


###########################################
# 📊 기술 트렌드 분석 (8주)
###########################################
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

        if job.tags:
            if isinstance(job.tags, list):
                for t in job.tags:
                    if isinstance(t, str):
                        skills.append(t)

        weekly_counter.update(skills)

    return [
        {"skill": skill, "count": count}
        for skill, count in weekly_counter.most_common()
    ]


###########################################
# 🎯 사용자 스킬 추출
###########################################
def get_user_skills(user: UserProfile):
    if not user:
        return []

    raw = user.tech_stack

    if isinstance(raw, list):
        return [s for s in raw if isinstance(s, str) and s.strip()]

    if isinstance(raw, str):
        return [s.strip() for s in raw.split(",") if s.strip()]

    return []


###########################################
# 🎯 사용자 맞춤 채용 추천
###########################################
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


###########################################
# 💾 CareerJob 단일 저장
###########################################
def save_job_posting(db: Session, job_data: dict):
    url = job_data.get("url")
    if not url:
        return False

    # 중복 체크
    exists = (
        db.query(CareerJob)
        .filter(CareerJob.url == url)
        .first()
    )
    if exists:
        return False

    title = job_data.get("title")
    norm_tags = normalize_tags(job_data.get("tags"), title=title)

    job = CareerJob(
        title=title,
        company=job_data.get("company"),
        location=job_data.get("location"),
        job_type=job_data.get("job_type"),
        url=url,
        tags=norm_tags,
        source=job_data.get("source", "Unknown"),
        posted_date=parse_posted_date(job_data.get("posted_date")),
        created_at=datetime.utcnow(),
    )

    try:
        db.add(job)
        db.commit()
        return True
    except Exception as e:
        print("❌ CareerJob Insert Error:", e)
        db.rollback()
        return False


###########################################
# 💾 리스트 일괄 저장
###########################################
def save_crawled_jobs(results: List[dict]):
    db = SessionLocal()
    saved = 0

    for job in results:
        if save_job_posting(db, job):
            saved += 1

    db.close()
    print(f"💾 CareerJob 저장 완료: {saved}개 / 총 {len(results)}개")


###########################################
# 🔥 NEWS 스타일 Career Pipeline (단일 파일 방식)
###########################################
def run_career_pipeline():
    print("\n🔥 CAREER PIPELINE START")

    # 1) JobKorea
    try:
        from services.jobkorea_scraper import crawl_jobkorea
        jk = crawl_jobkorea()
        print(f"📌 JobKorea 확보: {len(jk)}개")
    except Exception as e:
        print(f"❌ JobKorea 크롤링 오류:", e)
        jk = []

    # 2) Saramin
    try:
        from services.saramin_scraper import crawl_saramin
        sm = crawl_saramin()
        print(f"📌 Saramin 확보: {len(sm)}개")
    except Exception as e:
        print(f"❌ Saramin 크롤링 오류:", e)
        sm = []

    # 3) 저장
    all_jobs = jk + sm
    save_crawled_jobs(all_jobs)

    print(f"💾 CareerJob 저장 완료: {len(all_jobs)}개 크롤링됨")
    print("🔥 CAREER PIPELINE END\n")

###########################################
# ⭐ 신규: 채용 공고 페이징
###########################################
def get_jobs_paged(db: Session, page: int, size: int):
    """
    채용 공고 페이징 함수
    /api/career/jobs?page=1&size=6에서 사용됨
    """

    total = db.query(CareerJob).count()

    jobs = (
        db.query(CareerJob)
        .order_by(CareerJob.posted_date.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "page": page,
        "size": size,
        "total": total,
        "total_pages": (total + size - 1) // size,
        "jobs": jobs,
    }
