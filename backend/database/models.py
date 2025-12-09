# backend/database/models.py
# flake8: noqa
"""
📦 IT Trend Hub v4 Gamified — DB 모델
기존 DevHub 기능 + 게이미피케이션(Skill Tree) + Daily Quest 통합 버전
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text,
    JSON, Float, ForeignKey, Boolean, Enum
)
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum
import os
from sqlalchemy.dialects.mysql import LONGTEXT


# -------------------------------------------------------------------
# ⚙️ DB 연결 (기존 유지)
# -------------------------------------------------------------------
try:
    from database.mariadb import Base, engine
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "devhub_gamified.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ===================================================================
# 🎮 Skill Node Progress ENUM
# ===================================================================
class NodeStatus(str, enum.Enum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    COMPLETED = "COMPLETED"


# ===================================================================
# 👤 사용자 프로필 & 게임 스탯
# ===================================================================
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    level = Column(Integer, default=1)
    current_xp = Column(Integer, default=0)
    title = Column(String(50), default="Novice Explorer")

    main_focus = Column(String(50), default="career")
    role_type = Column(String(50))
    career_stage = Column(String(50))
    tech_stack = Column(JSON, default=[])
    interest_topics = Column(JSON, default=[])
    preferred_sources = Column(JSON, default=["News", "JobKorea", "GitHub", "Velog"])

    last_login = Column(DateTime, default=datetime.utcnow)
    activity_score = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    interests = relationship("UserInterest", backref="user", cascade="all, delete-orphan")
    histories = relationship("UserHistory", backref="user", cascade="all, delete-orphan")
    recommendations = relationship("UserRecommendation", backref="user", cascade="all, delete-orphan")

    progress = relationship("UserNodeProgress", backref="user", cascade="all, delete-orphan")
    dev_preference = relationship("DevUserPreference", backref="user", uselist=False, cascade="all, delete-orphan")

    today_quests = relationship("UserTodayQuests", backref="user", cascade="all, delete-orphan")
    quest_progress = relationship("UserQuestProgress", backref="user", cascade="all, delete-orphan")


# ===================================================================
# 🗺️ Skill Track
# ===================================================================
class SkillTrack(Base):
    __tablename__ = "skill_tracks"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), unique=True, index=True)
    title = Column(String(100))
    description = Column(Text)

    nodes = relationship("SkillNode", backref="track", cascade="all, delete-orphan")


# ===================================================================
# 🧩 Skill Node
# ===================================================================
class SkillNode(Base):
    __tablename__ = "skill_nodes"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("skill_tracks.id"))
    track_slug = Column(String(50), index=True)

    node_id = Column(String(50), index=True)
    label = Column(String(100))
    category = Column(String(50), nullable=True)
    description = Column(Text)

    icon_slug = Column(String(50))
    position = Column(JSON)
    prerequisites = Column(JSON, default=[])

    xp_reward = Column(Integer, default=100)
    difficulty = Column(String(20), default="easy")

    search_keywords = Column(JSON, default=[])
    resource_link = Column(String(500))
    thumbnail = Column(String(500))

    # ⭐ 대표 강의 (main quest)
    main_quest_id = Column(Integer, ForeignKey("learning_quests.id"), nullable=True)
    main_quest = relationship(
        "LearningQuest",
        foreign_keys=[main_quest_id],
        backref="main_of_nodes"
    )

    # ⭐ Daily Quests (여러개)
    quests = relationship(
        "LearningQuest",
        back_populates="node",
        cascade="all, delete-orphan",
        foreign_keys="LearningQuest.node_db_id"
    )




# ===================================================================
# 🎮 Skill Node Progress
# ===================================================================
class UserNodeProgress(Base):
    __tablename__ = "user_node_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"))
    node_db_id = Column(Integer, ForeignKey("skill_nodes.id"))

    status = Column(Enum(NodeStatus), default=NodeStatus.LOCKED)
    completed_at = Column(DateTime)
    interaction_count = Column(Integer, default=0)


# ===================================================================
# 🎮 LearningResource
# ===================================================================
class LearningResource(Base):
    __tablename__ = "learning_resources"

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    description = Column(Text)
    url = Column(String(500), unique=True)
    category = Column(String(255), nullable=True)

    resource_link = Column(String(500))
    thumbnail = Column(String(500))


# ===================================================================
# 📰 News Feed
# ===================================================================
class NewsFeed(Base):
    __tablename__ = "news_feed"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    summary = Column(Text)
    content = Column(LONGTEXT)
    category = Column(String(50))
    keywords = Column(JSON)
    source = Column(String(100))
    url = Column(String(500))
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 💬 Dev Community Posts
# ===================================================================
class DevPost(Base):
    __tablename__ = "dev_posts"

    id = Column(Integer, primary_key=True, index=True)

    source = Column(String(50), index=True)
    source_id = Column(String(255), index=True)
    title = Column(String(255))
    url = Column(String(500))
    author = Column(String(255))

    summary = Column(Text)
    tags = Column(JSON, default=[])

    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    published_at = Column(DateTime)
    crawled_at = Column(DateTime, default=datetime.utcnow)

    topic_primary = Column(String(50))
    issue_primary = Column(String(50))
    topic_ai = Column(String(50))
    issue_ai = Column(String(50))


# ===================================================================
# ⭐ Dev User Preferences
# ===================================================================
class DevUserPreference(Base):
    __tablename__ = "dev_user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))

    favorite_tags = Column(JSON, default=[])
    favorite_sources = Column(JSON, default=["okky", "tistory", "devto"])
    preference_score = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ===================================================================
# ⭐ DAILY QUEST — 생활코딩 기반 퀘스트 테이블
# ===================================================================
class LearningQuest(Base):
    __tablename__ = "learning_quests"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text)
    url = Column(String(500), nullable=False)

    xp = Column(Integer, default=50)
    difficulty = Column(String(20), default="easy")

    category = Column(String(50))
    chapter = Column(String(50))

    # ⭐ Daily Quest용 FK
    node_db_id = Column(Integer, ForeignKey("skill_nodes.id"), nullable=True)

    # ⭐ 여기에 foreign_keys 명시해야 충돌이 사라짐!!!
    node = relationship(
        "SkillNode",
        back_populates="quests",
        foreign_keys=[node_db_id]
    )

    completed = Column(Boolean, default=False)
    last_recommended = Column(String(20))





# ===================================================================
# ⭐ DAILY QUEST — 추천된 5개 저장 테이블
# ===================================================================
class UserTodayQuests(Base):
    __tablename__ = "user_today_quests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"))
    quest_id = Column(Integer, ForeignKey("learning_quests.id"))

    date_key = Column(String(20), index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    quest = relationship("LearningQuest")


# ===================================================================
# ⭐ DAILY QUEST — 퀘스트 완료 기록
# ===================================================================
class UserQuestProgress(Base):
    __tablename__ = "user_quest_progress"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user_profiles.id"))
    quest_id = Column(Integer, ForeignKey("learning_quests.id"))

    status = Column(String(20), default="pending")  # pending / completed
    completed_at = Column(DateTime)

    quest = relationship("LearningQuest")


# ===================================================================
# 🧩 User Interests
# ===================================================================
class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    keyword = Column(String(255))
    category = Column(String(50), default="general")
    created_at = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 🧩 User History
# ===================================================================
class UserHistory(Base):
    __tablename__ = "user_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    action_type = Column(String(50))
    target_table = Column(String(50))
    target_id = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 🧩 User Recommendation
# ===================================================================
class UserRecommendation(Base):
    __tablename__ = "user_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))

    source_type = Column(String(50))
    data_id = Column(Integer)
    score = Column(Float, default=0.0)
    reason = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 🚀 DB 초기화
# ===================================================================
def init_db():
    print("📦 Initializing DevHub Database (v4 Gamified + Daily Quest)...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created/updated successfully!")
