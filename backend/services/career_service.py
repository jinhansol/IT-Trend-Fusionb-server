# backend/services/career_service.py
# flake8: noqa

from collections import Counter
from datetime import datetime, timedelta
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
import json
import re

from database.mariadb import SessionLocal
from database.models import CareerJob, UserProfile

try:
    from services.career_scraper import crawl_career_all
except ImportError:
    print("⚠️ career_scraper 모듈을 찾을 수 없습니다.")
    def crawl_career_all(keyword, limit_per_site=20): return []

###########################################
# 🗂️ 기술 스택 카테고리 정의 (소문자 기준)
###########################################
TECH_CATEGORIES = {
    "frontend": {
        "javascript", "typescript", "react", "vue", "vue.js", "next.js", "nextjs",
        "html", "css", "svelte", "redux", "tailwind", "jquery", "bootstrap", "angular"
    },
    "backend": {
        "java", "spring", "spring boot", "springboot", "python", "django", "flask", "fastapi",
        "node.js", "node", "nestjs", "go", "golang", "kotlin", "php", "c#", ".net",
        "mysql", "postgresql", "oracle", "mongodb", "redis", "docker", "aws", "kubernetes"
    }
}

# 크롤링 검색어
CORE_KEYWORDS = ["Java", "Python", "JavaScript", "AI", "React", "Spring"]

# 키워드 매핑 (정규화)
KEYWORD_MAPPING = {
    "machine learning": "AI", "deep learning": "AI", 
    "react": "React", "reactjs": "React", "vue": "Vue.js", "vue.js": "Vue.js", "next": "Next.js", "next.js": "Next.js",
    "typescript": "TypeScript", "ts": "TypeScript", "javascript": "JavaScript", "js": "JavaScript",
    "python": "Python", "java": "Java", "spring": "Spring", "springboot": "Spring Boot", "spring boot": "Spring Boot",
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI", 
    "node": "Node.js", "node.js": "Node.js", "nestjs": "NestJS",
    "golang": "Go", "go": "Go", "kotlin": "Kotlin",
    "aws": "AWS", "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "mysql": "MySQL", "postgresql": "PostgreSQL", "redis": "Redis", "mongodb": "MongoDB"
}

###########################################
# 🛠️ 유틸리티 함수들
###########################################
def extract_skills_from_title(title: Optional[str]) -> List[str]:
    found: List[str] = []
    if not title: return found
    lower_title = title.lower()
    for keyword, tag_name in KEYWORD_MAPPING.items():
        if keyword in lower_title: 
            found.append(tag_name)
    return list(set(found))

def normalize_tags(raw_tags: Any, title: Optional[str] = None) -> List[str]:
    tags: List[str] = []
    if isinstance(raw_tags, list):
        for t in raw_tags:
            if isinstance(t, str) and t.strip(): tags.append(t.strip())
    elif isinstance(raw_tags, str):
        for t in raw_tags.split(","):
            tag = t.strip()
            if tag: tags.append(tag)
    
    if title: tags.extend(extract_skills_from_title(title))

    unique = {}
    for t in tags:
        lower_t = t.lower()
        final_name = KEYWORD_MAPPING.get(lower_t, t)
        unique[final_name] = final_name
        
    return list(unique.values())[:5]

def parse_posted_date(raw: Any) -> datetime:
    if isinstance(raw, datetime): return raw
    if isinstance(raw, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try: return datetime.strptime(raw, fmt)
            except ValueError: continue
    return datetime.utcnow()

# =========================================================
# 📊 [핵심 수정] 카테고리별 기술 트렌드 분석
# =========================================================
def get_tech_trends_by_category(db: Session, category: str, weeks: int = 8):
    """
    category: 'frontend' | 'backend'
    """
    # 1. 날짜 조건 없이, 무조건 최신 수집된 공고 1000개를 가져옵니다. (데이터 확보 우선)
    jobs = (
        db.query(CareerJob)
        .order_by(CareerJob.id.desc()) # ID 역순 (최신순)
        .limit(1000)
        .all()
    )
    
    target_skills = TECH_CATEGORIES.get(category, set())
    counter = Counter()

    print(f"📊 Analyzing {len(jobs)} jobs for {category}...") # 디버그 로그

    for job in jobs:
        raw_list = []
        tags_val = getattr(job, "tags", None)
        
        # 2. 태그 파싱 (강력하게)
        if tags_val:
            if isinstance(tags_val, list): 
                raw_list = tags_val
            elif isinstance(tags_val, str):
                try: 
                    # JSON 배열 ["A", "B"] 형태 시도
                    raw_list = json.loads(tags_val)
                except: 
                    # 그냥 콤마 문자열 "A, B" 형태 시도
                    raw_list = [t.strip() for t in tags_val.split(",") if t.strip()]
        
        # 3. 제목에서도 추출
        raw_list.extend(extract_skills_from_title(job.title))

        # 4. 카운팅 (소문자 변환 후 매칭)
        seen = set()
        for s in raw_list:
            if isinstance(s, str):
                s_clean = s.strip()
                s_lower = s_clean.lower()
                
                # 매핑된 정규화 이름도 확인 (예: reactjs -> react)
                norm_key = KEYWORD_MAPPING.get(s_lower, s_clean)
                norm_lower = norm_key.lower()
                
                # 해당 카테고리(프론트/백)에 속하는지 확인
                if (s_lower in target_skills or norm_lower in target_skills) and norm_lower not in seen:
                    counter[norm_key] += 1
                    seen.add(norm_lower)
    
    # 5. 결과 반환 (디버그 로그 포함)
    results = [{"skill": skill, "count": count} for skill, count in counter.most_common(6)]
    print(f"✅ {category} Trends: {results}")
    
    return results

# 기존 함수 (전체 트렌드)
def get_weekly_tech_trends(db: Session, weeks: int = 8):
    frontend = get_tech_trends_by_category(db, "frontend", weeks)
    backend = get_tech_trends_by_category(db, "backend", weeks)
    
    total_counter = Counter()
    for item in frontend + backend:
        total_counter[item['skill']] += item['count']
        
    return [{"skill": k, "count": v} for k, v in total_counter.most_common(10)]


# ... (나머지 get_recommended_jobs, save_job_posting 등 기존 함수 유지)
def get_recommended_jobs(db: Session, skills: list, limit: int = 20):
    query = db.query(CareerJob)
    if skills:
        filters = [CareerJob.title.ilike(f"%{skill}%") for skill in skills]
        filters.extend([CareerJob.tags.ilike(f"%{skill}%") for skill in skills])
        query = query.filter(or_(*filters))
    return query.order_by(CareerJob.posted_date.desc()).limit(limit).all()

def save_job_posting(db: Session, job_data: dict):
    url = job_data.get("url")
    if not url: return False
    if db.query(CareerJob).filter(CareerJob.url == url).first(): return False

    title = job_data.get("title")
    norm_tags = normalize_tags(job_data.get("tags"), title=title)

    job = CareerJob(
        title=title, company=job_data.get("company"), location=job_data.get("location"),
        job_type=job_data.get("job_type"), url=url, tags=norm_tags,
        source=job_data.get("source", "Unknown"),
        posted_date=parse_posted_date(job_data.get("posted_date")),
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    return True

def save_crawled_jobs(results: List[dict]):
    db = SessionLocal()
    saved = 0
    for job in results:
        try:
            if save_job_posting(db, job): saved += 1
        except Exception: db.rollback()
    db.close()
    print(f"💾 [Career] Saved {saved}/{len(results)} jobs.")

def run_career_pipeline():
    print("\n🔥 CAREER PIPELINE START")
    for keyword in CORE_KEYWORDS:
        try:
            results = crawl_career_all(keyword, limit_per_site=20)
            save_crawled_jobs(results)
        except Exception as e: print(f"❌ Pipeline Error ({keyword}): {e}")
    print("🔥 CAREER PIPELINE END\n")

def get_jobs_paged(db: Session, page: int, size: int):
    total = db.query(CareerJob).count()
    jobs = db.query(CareerJob).order_by(CareerJob.posted_date.desc()).offset((page - 1) * size).limit(size).all()
    return {"page": page, "size": size, "total": total, "total_pages": (total + size - 1) // size, "jobs": jobs}