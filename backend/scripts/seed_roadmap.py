# backend/scripts/seed_roadmap.py
# flake8: noqa

import sys, os
from sqlalchemy.orm import Session

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.mariadb import SessionLocal
from database.models import SkillTrack, SkillNode, LearningQuest
from services.roadmap_scraper import crawl_life_coding_library


# ============================================================
# 공통: Quest 생성 함수
# ============================================================
def create_quest(db, title, desc, url, track_slug, node_db_id):
    quest = LearningQuest(
        title=title,
        description=desc,
        url=url, 
        xp=50,
        difficulty="medium",
        category=track_slug,
        chapter=title,
        node_db_id=node_db_id,
        completed=False 
    )
    db.add(quest)
    db.flush()
    return quest.id


# ============================================================
# 1) Public 트랙 (Web Roadmap - 고정 커리큘럼)
# ============================================================
PUBLIC_NODES = [
    ("WEB-01", "Web 개념 & 인터넷", "개발자의 필수 상식: 인터넷의 작동 원리", "https://opentutorials.org/course/3084/18889"),
    ("WEB-02", "HTML (뼈대 만들기)", "웹 페이지의 구조를 잡는 마크업 언어", "https://opentutorials.org/course/3084"),
    ("WEB-03", "CSS (디자인)", "웹을 아름답게 꾸미는 스타일 시트", "https://opentutorials.org/course/3086"),
    ("WEB-04", "JavaScript (동적 기능)", "웹에 생명을 불어넣는 프로그래밍 언어", "https://opentutorials.org/course/3085"),
    ("WEB-05", "React (UI 라이브러리)", "컴포넌트 기반의 현대적 웹 개발", "https://opentutorials.org/course/1"),
    ("WEB-06", "Server & Network", "서버의 역할과 통신 이해하기", "https://opentutorials.org/course/1"),
    ("WEB-07", "Database (데이터 저장)", "데이터의 저장과 관리를 위한 필수 기술", "https://opentutorials.org/course/3161"),
    ("WEB-08", "Python / Node.js", "서버 사이드 프로그래밍 기초", "https://opentutorials.org/course/1"),
    ("WEB-09", "Git & 협업", "버전 관리 시스템과 GitHub 활용", "https://opentutorials.org/course/2708"),
    ("WEB-10", "Career AI 나침반", "내 성향에 맞는 직무(FE/BE) 분석받기", "internal://compass"), 
]

def seed_public_track(db):
    track = SkillTrack(
        slug="web-roadmap",
        title="Web Developer Roadmap",
        description="웹 개발자 입문: 프론트엔드와 백엔드의 갈림길"
    )
    db.add(track)
    db.commit()
    db.refresh(track)

    prev_node_id = None
    for idx, (node_id, title, desc, url) in enumerate(PUBLIC_NODES, start=1):
        node = SkillNode(
            track_id=track.id,
            track_slug="web-roadmap",
            node_id=node_id,
            label=title,
            description=desc,
            resource_link=url,
            xp_reward=40,
            position=idx,
            prerequisites=[prev_node_id] if prev_node_id else []
        )
        db.add(node)
        db.flush()
        create_quest(db, title, desc, url, "web-roadmap", node.id)
        prev_node_id = node.node_id 

    db.commit()
    print("✅ Public Web Roadmap 생성 완료!")


# ============================================================
# 2) Personal 트랙 (⭐ FE / BE 단계 확장)
# ============================================================
def seed_personal_track(db):
    lessons = crawl_life_coding_library()
    print(f"📚 생활코딩 강의 {len(lessons)}개 수집됨 -> 분류 작업 시작")

    track = SkillTrack(
        slug="life-coding",
        title="생활코딩 실전 로드맵",
        description="수집된 강의를 공통/프론트/백엔드 트랙으로 자동 분류하여 제공합니다.",
    )
    db.add(track)
    db.commit()
    db.refresh(track)

    if not lessons:
        return

    # ⭐ [핵심 수정] 노드 단계를 더 세분화했습니다! (4단계씩)
    CATEGORIES = [
        # --- Root ---
        {"label": "Web Essentials", "id": "LC-01", "keys": ["WEB1", "웹", "인터넷", "HTML", "Domain", "HTTP"], "parent": None},
        
        # --- Frontend Branch (4 Steps) ---
        {"label": "HTML/CSS Basic", "id": "LC-FE-01", "keys": ["CSS", "Design", "UI", "Layout"], "parent": "LC-01"},
        {"label": "JavaScript Core", "id": "LC-FE-02", "keys": ["JavaScript", "자바스크립트", "JS", "ECMA"], "parent": "LC-FE-01"},
        {"label": "React & UI Lib",  "id": "LC-FE-03", "keys": ["React", "리액트", "Vue", "Component"], "parent": "LC-FE-02"},
        {"label": "State & Next.js", "id": "LC-FE-04", "keys": ["Redux", "Next", "State", "Ajax", "jQuery"], "parent": "LC-FE-03"},
        
        # --- Backend Branch (4 Steps) ---
        {"label": "Server & Linux",  "id": "LC-BE-01", "keys": ["Server", "서버", "Linux", "리눅스", "Ubuntu"], "parent": "LC-01"},
        {"label": "Python & Node",   "id": "LC-BE-02", "keys": ["Python", "파이썬", "Java", "자바", "Node", "PHP"], "parent": "LC-BE-01"},
        {"label": "Database & SQL",  "id": "LC-BE-03", "keys": ["Database", "데이터베이스", "MySQL", "Oracle", "SQL", "MongoDB"], "parent": "LC-BE-02"},
        {"label": "DevOps & Cloud",  "id": "LC-BE-04", "keys": ["Docker", "AWS", "Cloud", "Deploy", "배포", "Nginx"], "parent": "LC-BE-03"},
        
        # --- Others ---
        {"label": "Deep Dive", "id": "LC-ADV", "keys": [], "parent": "LC-01"} 
    ]

    node_objects = {}
    
    # 2. 노드 생성
    for idx, cat in enumerate(CATEGORIES, start=1):
        parent_id = cat["parent"]
        parents = [node_objects[parent_id].node_id] if parent_id and parent_id in node_objects else []

        node = SkillNode(
            track_id=track.id,
            track_slug="life-coding",
            node_id=cat["id"],
            label=cat["label"],
            description=f"{cat['label']} 관련 실습 강의 모음",
            xp_reward=100,
            position=idx,
            prerequisites=parents,
            thumbnail=None
        )
        db.add(node)
        db.flush()
        node_objects[cat["id"]] = node

    # 3. 강의(Quest) 자동 분류 및 삽입
    count = 0
    for lec in lessons:
        title = lec["title"]
        target_node = node_objects["LC-ADV"] # 기본값

        # 키워드 매칭 (위 카테고리 순서대로 검사)
        for cat in CATEGORIES:
            if any(k.lower() in title.lower() for k in cat["keys"]):
                target_node = node_objects[cat["id"]]
                break
        
        create_quest(
            db, 
            title=lec["title"], 
            desc=lec["description"], 
            url=lec["resource_link"], 
            track_slug="life-coding", 
            node_db_id=target_node.id
        )
        count += 1

    db.commit()
    print(f"🎉 Personal 트랙: {count}개 강의가 풍성한 단계로 분류되었습니다!")


# ============================================================
# 메인 실행
# ============================================================
def seed_roadmaps(db: Session):
    print("🔥 [Seeding] 로드맵 생성 시작...")
    seed_public_track(db)
    seed_personal_track(db)
    print("🎉 모든 로드맵 생성 완료!")

if __name__ == "__main__":
    seed_roadmaps(SessionLocal())