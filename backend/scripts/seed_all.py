# backend/scripts/seed_all.py
# flake8: noqa

import sys, os
from sqlalchemy import text  # ⭐ SQL 직접 실행을 위해 추가

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.mariadb import SessionLocal
from database.models import (
    SkillTrack, SkillNode, LearningQuest, 
    UserNodeProgress, UserQuestProgress, UserTodayQuests
)
from scripts.seed_roadmap import seed_roadmaps


# -----------------------------------------------------------
# 전체 데이터 초기화 (강제 삭제 모드)
# -----------------------------------------------------------
def reset_all_tables(db):
    print("\n🧨 초기화 중: FK 체크 끄고 데이터 강제 삭제...")

    # ⭐ 1. 외래키 검사 비활성화 (순환 참조 무시)
    db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

    # 2. 데이터 삭제 (순서 상관 없음)
    db.query(UserNodeProgress).delete()
    db.query(UserQuestProgress).delete()
    db.query(UserTodayQuests).delete()
    db.query(LearningQuest).delete()
    db.query(SkillNode).delete()
    db.query(SkillTrack).delete()

    # ⭐ 3. 외래키 검사 다시 활성화
    db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

    db.commit()
    print("✔ 테이블 초기화 완료! (깨끗해요 ✨)\n")


# -----------------------------------------------------------
# 메인 실행 함수
# -----------------------------------------------------------
def seed_all():
    print("🔍 DB 연결 중...")

    print("""
===============================
   🚀 SEED ALL (Roadmap + Quest)
===============================
    """)

    db = SessionLocal()

    try:
        # ---------------------------
        # 1) 전체 초기화
        # ---------------------------
        reset_all_tables(db)

        # ---------------------------
        # 2) 로드맵 + 퀘스트 생성
        # ---------------------------
        seed_roadmaps(db)

        print("\n🎉 ALL DATA SEEDED SUCCESSFULLY! 🎉\n")
    
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        db.rollback()
    
    finally:
        db.close()


# -----------------------------------------------------------
# 실행
# -----------------------------------------------------------
if __name__ == "__main__":
    seed_all()