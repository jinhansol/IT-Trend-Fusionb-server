# backend/scripts/force_reset.py
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mariadb import engine, Base
from scripts.seed_roadmap import seed_data

def reset_database():
    print("💥 [Danger] 기존 데이터베이스 테이블을 모두 삭제합니다...")
    
    # 1. 모든 테이블 삭제 (DROP TABLE)
    # 이 명령어가 기존의 낡은 skill_nodes 테이블을 날려버립니다.
    Base.metadata.drop_all(bind=engine)
    print("🗑️  Tables dropped.")

    # 2. 테이블 다시 생성 (CREATE TABLE)
    # 이제 resource_link 컬럼이 포함된 새 테이블이 만들어집니다.
    print("🏗️  Creating new tables with updated schema...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created.")

    # 3. 데이터 채우기 (Seed)
    print("🌱 Seeding data...")
    seed_data()
    print("✨ DB Reset & Seed Completed Successfully!")

if __name__ == "__main__":
    reset_database()