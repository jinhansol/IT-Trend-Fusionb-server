# backend/services/quest_generator.py
# flake8: noqa

import re
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import LearningQuest, SkillNode


# ================================================================
# 1) 정규식 기반 카테고리 자동 분류 규칙 (fallback 용)
# ================================================================
CATEGORY_RULES = [
    (r"html|태그", "html", "easy", "web-basic"),
    (r"css|스타일", "css", "easy", "web-basic"),
    (r"javascript|js|dom|이벤트", "js", "normal", "web-basic"),
    (r"git|github|버전", "git", "easy", "tools"),
    (r"python|파이썬", "python", "normal", "backend"),
    (r"django|flask|백엔드", "python", "hard", "backend"),
    (r"database|sql|mysql|db", "db", "normal", "database"),
    (r"react|리액트", "react", "hard", "frontend"),
    (r"node|express", "node", "hard", "backend"),
    (r"linux|shell|terminal", "linux", "normal", "tools"),
]


def classify_static_category(title: str, description: str):
    """
    기존 정규식 기반 카테고리·난이도 매핑 (fallback 용)
    """
    text = f"{title} {description}".lower()

    for pattern, category, difficulty, chapter in CATEGORY_RULES:
        if re.search(pattern, text):
            return category, difficulty, chapter

    return "general", "easy", "general"


# ================================================================
# 2) 난이도 → XP 매핑
# ================================================================
DIFFICULTY_XP = {
    "easy": 30,
    "normal": 50,
    "hard": 80,
}


def get_xp(difficulty: str):
    return DIFFICULTY_XP.get(difficulty, 40)


# ================================================================
# 3) Node 기반 분류 (우선순위 가장 높음)
# ================================================================
def classify_by_node(db: Session, title: str, desc: str):
    """
    제목/설명을 기준으로 SkillNode와 매칭하는 기능.
    Node.label 또는 Node.search_keywords에 매칭되면
    Quest.category = Node.slug 또는 Node.label 로 설정
    """

    text = f"{title} {desc}".lower()
    nodes = db.query(SkillNode).all()

    for node in nodes:
        # label 기반 매칭
        if node.label and node.label.lower() in text:
            return node

        # keyword 기반 매칭
        if node.search_keywords:
            for kw in node.search_keywords:
                if kw.lower() in text:
                    return node

    return None  # 매칭되는 Node 없음


# ================================================================
# 4) Quest 자동 생성 (Node 우선 → static fallback)
# ================================================================
def generate_quests_from_courses(db: Session, courses: list):
    """
    크롤러로 수집된 courses 리스트를 기반으로 Quest 자동 생성.
    Node 기반 분류 → fallback 정규식 기반 분류 순으로 적용.
    """

    inserted = 0

    for c in courses:
        title = c.get("title", "Untitled")
        desc = c.get("description", "")
        url = c.get("resource_link")

        # URL 기반 중복 방지 강화
        exists = db.query(LearningQuest).filter_by(url=url).first()
        if exists:
            continue

        # ---------------------------------------
        # 1) Node 기반 분류 (최우선)
        # ---------------------------------------
        matched_node = classify_by_node(db, title, desc)

        if matched_node:
            category = matched_node.label  # 또는 matched_node.track_id 등 선택 가능
            difficulty = matched_node.difficulty or "normal"
            chapter = matched_node.node_id  # Node 자체를 Chapter로 활용
        else:
            # ---------------------------------------
            # 2) 정규식 기반 카테고리 (fallback)
            # ---------------------------------------
            category, difficulty, chapter = classify_static_category(title, desc)

        # XP 계산
        xp = get_xp(difficulty)

        # 최종 Quest 생성
        quest = LearningQuest(
            title=title,
            description=desc,
            url=url,
            xp=xp,
            difficulty=difficulty,
            category=category,
            chapter=chapter,
            completed=False,
            last_recommended=None,
        )

        db.add(quest)
        inserted += 1

    db.commit()
    return inserted


# ================================================================
# 5) 생활코딩 기본 Quest 생성 (정적 세트)
# ================================================================
LIFE_CODING_COURSES = [
    {"title": "HTML 태그 소개", "description": "HTML 구조", "url": "https://opentutorials.org/course/3084/intro"},
    {"title": "CSS 기초 문법", "description": "CSS 기초", "url": "https://opentutorials.org/course/3086/basic"},
    {"title": "JavaScript 변수와 함수", "description": "JS 함수", "url": "https://opentutorials.org/course/3085/basic"},
    {"title": "Python 기초 문법", "description": "Python 구조", "url": "https://opentutorials.org/course/1/python-basic"},
    {"title": "Node.js 기본 구조", "description": "Node 기초", "url": "https://opentutorials.org/course/3332/basic"},
]


def generate_static_lifecoding_quests(db: Session):
    created = 0

    for item in LIFE_CODING_COURSES:
        exists = db.query(LearningQuest).filter_by(url=item["url"]).first()
        if exists:
            continue

        category, difficulty, chapter = classify_static_category(
            item["title"], item["description"]
        )

        quest = LearningQuest(
            title=item["title"],
            description=item["description"],
            url=item["url"],
            xp=get_xp(difficulty),
            difficulty=difficulty,
            category=category,
            chapter=chapter,
            completed=False,
        )

        db.add(quest)
        created += 1

    db.commit()
    return created


# ================================================================
# 6) 전체 일괄 생성
# ================================================================
def seed_all_quests(db: Session):
    static_added = generate_static_lifecoding_quests(db)
    return {"static_courses_added": static_added}


# ================================================================
# 7) Quest 전체 리프레시 (크롤러 기반)
# ================================================================
def refresh_learning_quests(db: Session):
    """
    기존 LearningQuest 전체 삭제 후 최신 크롤링 기준으로 재생성.
    """

    db.query(LearningQuest).delete()
    db.commit()

    try:
        from services.crawler_life_coding import fetch_life_coding_courses
        courses = fetch_life_coding_courses()
    except:
        courses = LIFE_CODING_COURSES

    count = generate_quests_from_courses(db, courses)
    return count


# ================================================================
# 실행 테스트
# ================================================================
if __name__ == "__main__":
    from database.mariadb import SessionLocal
    db = SessionLocal()
    print(seed_all_quests(db))
