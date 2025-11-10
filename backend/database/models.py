# backend/database/models.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# ⚙️ DB 연결 (지금은 SQLite, 나중에 MariaDB로 쉽게 교체 가능)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "user_data.db")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 🧠 사용자 관심 키워드 테이블
class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False)
    category = Column(String(100), default="general")  # ex: 'career', 'learn', 'trend'
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    """DB 초기화"""
    Base.metadata.create_all(bind=engine)
# flake8: noqa
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from database.mariadb import Base

# 🧠 사용자 관심 키워드
class UserInterest(Base):
    __tablename__ = "user_interests"
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False)
    category = Column(String(100), default="general")
    created_at = Column(DateTime, default=datetime.utcnow)


# 📰 뉴스 데이터
class NewsFeed(Base):
    __tablename__ = "news_feed"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    source = Column(String(100))
    url = Column(String(500), nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


# 💼 채용 정보
class CareerJob(Base):
    __tablename__ = "career_jobs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    company = Column(String(255))
    location = Column(String(255))
    job_type = Column(String(100))
    link = Column(String(500))
    posted_date = Column(DateTime, default=datetime.utcnow)


# 📊 기술 트렌드
class TechTrend(Base):
    __tablename__ = "tech_trends"
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255))
    summary = Column(Text)
    trend_score = Column(Integer, default=0)
    source = Column(String(100))
    fetched_at = Column(DateTime, default=datetime.utcnow)


# ✅ DB 초기화
def init_db():
    from database.mariadb import engine
    print("📦 Creating tables in MariaDB...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")
