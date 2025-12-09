# backend/routers/ai_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from services.ai_service import chat_with_ai

router = APIRouter(tags=["AI Career Compass"])

# 요청 데이터 구조 (대화 내역)
class ChatRequest(BaseModel):
    messages: List[dict] # [{"role": "user", "content": "..."}]

@router.post("/chat")
def chat(request: ChatRequest):
    """
    사용자의 메시지를 받아 AI의 답변을 반환합니다.
    """
    try:
        ai_reply = chat_with_ai(request.messages)
        return {"role": "assistant", "content": ai_reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))