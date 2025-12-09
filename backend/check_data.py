# backend/check_data.py
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.mariadb import SessionLocal
from database.models import SkillNode, LearningQuest

def check_connection():
    db = SessionLocal()
    
    # 1. Web 개념 노드 찾기
    node = db.query(SkillNode).filter(SkillNode.label.like("%Web 개념%")).first()
    
    if not node:
        print("❌ 'Web 개념' 노드를 찾을 수 없습니다. 시드 스크립트를 먼저 실행하세요.")
        return

    print(f"📍 노드 확인: [{node.node_id}] {node.label} (DB ID: {node.id})")

    # 2. 연결된 퀘스트 확인 (Relationship)
    print(f"   ↳ 연결된 퀘스트 개수(node.quests): {len(node.quests)}개")
    
    # 3. 실제 Quest 테이블 확인
    quests = db.query(LearningQuest).filter(LearningQuest.chapter == node.label).all()
    print(f"   ↳ 이름으로 찾은 퀘스트 개수: {len(quests)}개")
    
    for q in quests:
        status = "✅ 연결됨" if q.node_db_id == node.id else "❌ 끊김 (node_db_id is NULL)"
        print(f"      - [Quest {q.id}] {q.title} -> {status}")

if __name__ == "__main__":
    check_connection()