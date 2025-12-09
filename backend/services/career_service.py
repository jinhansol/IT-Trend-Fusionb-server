# # backend/services/career_service.py
# # flake8: noqa

# """
# 🚫 [Deprecated] 
# CareerJob 테이블 삭제로 인해 더 이상 사용되지 않는 서비스입니다.
# 추후 AI Career Compass 기능 구현 시 완전히 새로 작성될 예정입니다.
# """

# from sqlalchemy.orm import Session

# # ---------------------------------------------------------
# #  dummy functions to prevent import errors
# # ---------------------------------------------------------

# def get_weekly_tech_trends(db: Session, weeks: int = 8):
#     return []

# def get_recommended_jobs(db: Session, skills: list, limit: int = 20):
#     return []

# def get_jobs_paged(db: Session, page: int, size: int):
#     return {"jobs": [], "total": 0}

# def run_career_pipeline():
#     print("⚠️ Career Pipeline is disabled.")
#     pass