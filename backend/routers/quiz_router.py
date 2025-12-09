# backend/routers/quiz_router.py
from fastapi import APIRouter
import random

router = APIRouter()

# 생활코딩 스타일의 기초~중급 문제 은행 (AI가 생성했다고 가정)
QUESTION_BANK = [
    {"id": 1, "category": "Frontend", "q": "HTML에서 하이퍼링크를 생성하는 태그는?", "options": ["<link>", "<a>", "<href>", "<src>"], "answer": "<a>"},
    {"id": 2, "category": "Frontend", "q": "CSS에서 요소를 보이지 않게 하되, 공간은 차지하게 하는 속성은?", "options": ["display: none", "visibility: hidden", "opacity: 0", "z-index: -1"], "answer": "visibility: hidden"},
    {"id": 3, "category": "Frontend", "q": "React에서 상태(State)를 관리하기 위해 사용하는 훅은?", "options": ["useEffect", "useState", "useContext", "useReducer"], "answer": "useState"},
    {"id": 4, "category": "Backend", "q": "다음 중 관계형 데이터베이스(RDBMS)가 아닌 것은?", "options": ["MySQL", "PostgreSQL", "Oracle", "MongoDB"], "answer": "MongoDB"},
    {"id": 5, "category": "Backend", "q": "HTTP 상태 코드 중 '페이지를 찾을 수 없음'을 의미하는 것은?", "options": ["200", "403", "404", "500"], "answer": "404"},
    {"id": 6, "category": "Backend", "q": "Python에서 패키지를 설치할 때 사용하는 명령어는?", "options": ["npm install", "pip install", "brew install", "apt-get"], "answer": "pip install"},
    {"id": 7, "category": "CS", "q": "자료구조 중 '선입선출(FIFO)' 방식을 따르는 것은?", "options": ["Stack", "Queue", "Tree", "Graph"], "answer": "Queue"},
    {"id": 8, "category": "CS", "q": "Git에서 변경 사항을 저장소에 기록하는 명령어는?", "options": ["git add", "git push", "git commit", "git checkout"], "answer": "git commit"},
    {"id": 9, "category": "Tools", "q": "리눅스에서 현재 디렉토리의 파일 목록을 보는 명령어는?", "options": ["cd", "pwd", "ls", "mkdir"], "answer": "ls"},
    {"id": 10, "category": "Tools", "q": "컨테이너화 기술의 대표적인 도구는?", "options": ["Docker", "Jenkins", "Ansible", "Terraform"], "answer": "Docker"},
]

@router.get("/generate")
def generate_quiz():
    # 랜덤으로 5~10문제 뽑아서 전달
    selected_questions = random.sample(QUESTION_BANK, k=5) 
    return {"questions": selected_questions}

@router.post("/submit")
def submit_quiz(answers: dict):
    # 정답 체크 및 점수 계산 로직
    # (여기서는 간단히 랜덤한 분석 결과를 리턴해주는 척합니다)
    return {
        "score": 80,
        "stats": [
            {"subject": "Frontend", "A": random.randint(40, 90), "fullMark": 100},
            {"subject": "Backend", "A": random.randint(40, 90), "fullMark": 100},
            {"subject": "CS Knowledge", "A": random.randint(30, 80), "fullMark": 100},
            {"subject": "AI/Data", "A": random.randint(20, 70), "fullMark": 100},
            {"subject": "Dev Tools", "A": random.randint(50, 100), "fullMark": 100},
            {"subject": "Communication", "A": random.randint(60, 90), "fullMark": 100},
        ],
        "message": "훌륭합니다! 백엔드 지식이 특히 돋보이네요."
    }