# backend/database/mariadb.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수 가져오기 (없을 경우 기본값 사용)
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "1234")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "it_trend_hub")

# DB 접속 URL 생성
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
print(f"🔍 DB_URL: {DB_URL}")

# 엔진 생성 (pool_pre_ping=True: 연결 끊김 방지)
engine = create_engine(DB_URL, pool_pre_ping=True)

# 세션 생성기
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# 모델들이 상속받을 Base 클래스
Base = declarative_base()

# ---------------------------------------------------------
# ✅ [수정 완료] 라우터에서 사용할 DB 세션 의존성 함수
# 이 함수가 없어서 ImportError가 발생했었습니다.
# ---------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()