# # backend/routers/career_router.py
# # flake8: noqa

# from fastapi import APIRouter, Depends, Query
# from sqlalchemy.orm import Session
# from typing import Optional
# import json
# import re

# from database.mariadb import SessionLocal
# from core.security import get_current_user_optional
# from services.career_service import (
#     get_weekly_tech_trends,
#     get_recommended_jobs,
#     get_jobs_paged,
#     get_tech_trends_by_category,  # 차트 분리용
#     run_career_pipeline           # ✅ [추가] 수동 갱신용
# )

# router = APIRouter(prefix="/api/career", tags=["Career Dashboard"])

# # -------------------------------------------------
# # 🛠️ 유틸리티: JSON 파싱 헬퍼
# # -------------------------------------------------
# def parse_json_field(field_data):
#     if not field_data: return []
#     if isinstance(field_data, list): return field_data
#     if isinstance(field_data, str):
#         try: return json.loads(field_data)
#         except: return [s.strip() for s in re.sub(r"[\[\]\"']", "", field_data).split(",") if s.strip()]
#     return []

# # -------------------------
# # 🔌 DB 연결 의존성
# # -------------------------
# def get_db():
#     db = SessionLocal()
#     try: yield db
#     finally: db.close()

# # -------------------------
# # 🛠️ 데이터 직렬화 헬퍼
# # -------------------------
# def serialize_job(job):
#     # 태그 중복 제거 로직
#     raw_tags = job.tags or []
#     if isinstance(raw_tags, str):
#         try: raw_tags = json.loads(raw_tags)
#         except: raw_tags = [t.strip() for t in raw_tags.split(",")]
#     unique_tags = list(set(raw_tags)) 

#     return {
#         "id": job.id, "title": job.title, "company": job.company,
#         "location": job.location, "job_type": job.job_type, "url": job.url,
#         "tags": unique_tags, "source": job.source,
#         "posted_date": job.posted_date, "created_at": job.created_at,
#     }

# # -------------------------------------------------
# # 🧠 기술별 스마트 학습 링크 매핑 함수
# # -------------------------------------------------
# def get_smart_learning_link(skill: str):
#     s = skill.lower()
#     if "react" in s: return "https://react.dev/learn"
#     if "next" in s: return "https://nextjs.org/learn"
#     if "vue" in s: return "https://vuejs.org/guide/introduction.html"
#     if "django" in s: return "https://docs.djangoproject.com/ko/5.0/intro/"
#     if "spring" in s: return "https://spring.io/guides"
#     if "docker" in s: return "https://docs.docker.com/get-started/"
#     if "kubernetes" in s: return "https://kubernetes.io/ko/docs/tutorials/"
#     if "git" in s: return "https://git-scm.com/doc"
    
#     base_yt = "https://www.youtube.com/results?search_query="
#     if "python" in s: return f"{base_yt}파이썬+기초+강의"
#     if "java" in s: return f"{base_yt}자바+입문+강의"
#     if "javascript" in s or "js" in s: return f"{base_yt}자바스크립트+기초"
#     if "typescript" in s or "ts" in s: return f"{base_yt}타입스크립트+기초"
#     if "aws" in s: return f"{base_yt}AWS+기초+사용법"
#     if "ai" in s or "ml" in s: return f"{base_yt}인공지능+머신러닝+기초"
#     if "sql" in s or "db" in s: return f"{base_yt}SQL+기초"
    
#     return f"https://www.inflearn.com/courses?s={skill}&price=free"


# # -------------------------------------------------
# # 📊 Career Dashboard
# # -------------------------------------------------
# @router.get("/dashboard")
# def career_dashboard(
#     current_user = Depends(get_current_user_optional),
#     db: Session = Depends(get_db)
# ):
#     mode = "public"
#     user_skills = []
    
#     if current_user:
#         tech = parse_json_field(current_user.tech_stack)
#         interest = parse_json_field(current_user.interest_topics)
#         user_skills = list(set(tech + interest))
#         if user_skills:
#             mode = "personalized"

#     if mode == "personalized":
#         recommended = get_recommended_jobs(db, skills=user_skills, limit=200)
#         if not recommended:
#             mode = "public"
#             jobs_page = get_jobs_paged(db, page=1, size=200)
#             jobs = [serialize_job(j) for j in jobs_page["jobs"]]
#         else:
#             jobs = [serialize_job(j) for j in recommended]
#     else:
#         jobs_page = get_jobs_paged(db, page=1, size=200)
#         jobs = [serialize_job(j) for j in jobs_page["jobs"]]

#     # ✅ 프론트엔드/백엔드 트렌드 분리 전달
#     frontend_trends = get_tech_trends_by_category(db, "frontend")
#     backend_trends = get_tech_trends_by_category(db, "backend")

#     return {
#         "mode": mode,
#         "jobs": jobs,
#         "frontend_trends": frontend_trends, 
#         "backend_trends": backend_trends,   
#         "user_skills": user_skills,
#     }


# # -------------------------------------------------
# # 📚 학습 추천 (Hybrid 로직)
# # -------------------------------------------------
# @router.get("/learning")
# def career_learning(
#     current_user = Depends(get_current_user_optional), 
#     db: Session = Depends(get_db)
# ):
#     global_trends = get_weekly_tech_trends(db)
#     trend_skills = [t["skill"] for t in global_trends]

#     personal_skills = []
#     if current_user:
#         tech = parse_json_field(current_user.tech_stack)
#         interest = parse_json_field(current_user.interest_topics)
#         raw_list = tech + interest
        
#         seen = set()
#         for s in raw_list:
#             if s and s not in seen:
#                 personal_skills.append(s)
#                 seen.add(s)

#     final_items = []
#     EXCLUDE_KEYWORDS = ["frontend", "backend", "fullstack", "devops", "mobile", "security", "ai / ml", "data eng.", "cloud", "embedded", "blockchain"]
    
#     for skill in personal_skills:
#         if skill.lower() not in EXCLUDE_KEYWORDS:
#             final_items.append({"skill": skill, "type": "mylike"})

#     for skill in trend_skills:
#         if len(final_items) >= 6: break
#         is_exist = any(item["skill"].lower() == skill.lower() for item in final_items)
#         if not is_exist:
#             final_items.append({"skill": skill, "type": "trend"})

#     learning_list = []
#     for item in final_items[:6]:
#         skill = item["skill"]
#         is_my_pick = (item["type"] == "mylike")
        
#         learning_list.append({
#             "tag": skill,
#             "title": f"{skill} 핵심 공략",
#             "desc": "선택하신 관심 분야와 관련된 추천 학습 자료입니다." if is_my_pick else "현재 채용 시장에서 수요가 급증하고 있는 기술입니다.",
#             "link": get_smart_learning_link(skill),
#             "source": "My Pick" if is_my_pick else "Hot Trend"
#         })

#     return {"learning": learning_list}


# # -------------------------------------------------
# # 📄 채용 공고 페이징
# # -------------------------------------------------
# @router.get("/jobs")
# def career_jobs(page: int = 1, size: int = 20, db: Session = Depends(get_db)):
#     result = get_jobs_paged(db, page, size)
#     result["jobs"] = [serialize_job(j) for j in result["jobs"]]
#     return result


# # -------------------------------------------------
# # 🔄 [추가] 워크넷 데이터 수동 갱신 (테스트용)
# # -------------------------------------------------
# @router.post("/refresh")
# def refresh_jobs():
#     """
#     [관리자/테스트용] 워크넷 API 파이프라인을 수동으로 실행합니다.
#     """
#     try:
#         run_career_pipeline()
#         return {"message": "✅ Worknet pipeline executed successfully."}
#     except Exception as e:
#         return {"message": f"❌ Error executing pipeline: {str(e)}"}