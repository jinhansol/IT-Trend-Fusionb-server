# services/career_service.py
from sqlalchemy.orm import Session
from database.models import CareerJob, UserProfile
from collections import Counter
from datetime import datetime, timedelta

# 분석 대상 기술 키워드 사전
TECH_KEYWORDS = [
    "Python", "React", "Node", "TypeScript", "Vue",
    "Next.js", "Java", "Spring", "Django", "Flutter",
    "AWS", "Kubernetes", "Docker", "AI", "ML", "Data"
]

def extract_skills_from_title(title: str):
    found = []
    for skill in TECH_KEYWORDS:
        if skill.lower() in title.lower():
            found.append(skill)
    return found


# ======================
# 기술 트렌드 분석 로직
# ======================
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


# ======================
# 추천 채용 공고 로직
# ======================
def get_recommended_jobs(db: Session, skills: list, limit: int = 20):
    if not skills:
        return []

    query = db.query(CareerJob)

    filters = []
    for skill in skills:
        filters.append(CareerJob.title.ilike(f"%{skill}%"))

    results = (
        query.filter(*filters)
        .order_by(CareerJob.posted_date.desc())
        .limit(limit)
        .all()
    )

    return results


# ======================
# 사용자 관심 기술 가져오기
# ======================
def get_user_skills(user: UserProfile):
    if user.favorite_skills:
        return user.favorite_skills.split(",")
    return []
