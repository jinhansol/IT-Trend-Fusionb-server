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
