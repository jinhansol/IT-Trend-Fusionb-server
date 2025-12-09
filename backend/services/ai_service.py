# backend/services/ai_service.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# 🤖 AI 페르소나: 직무 적성 검사관
SYSTEM_PROMPT = """
너는 개발자 지망생의 성향을 분석해주는 'IT 커리어 나침반'이야.
사용자와 대화를 나누며 그들의 성향이 [Frontend, Backend, AI/Data] 중 어디에 가까운지 파악해줘.

[대화 전략]
1. "눈에 보이는 결과를 바로 확인하는 게 좋나요, 아니면 보이지 않는 논리적 구조를 짜는 게 좋나요?" 같은 양자택일 질문을 던져.
2. 3~4턴 이내로 대화를 마무리하고 결론을 내려.
3. 사용자의 답변을 바탕으로 왜 그 직무가 어울리는지 칭찬과 함께 설명해줘.

[🌟 핵심: 결과 태그 (반드시 마지막 줄에 포함)]
분석이 끝나면, 추천하는 직무에 따라 아래 태그 중 하나를 **반드시** 붙여. 프론트엔드는 UI의 변화를 잘 다루고, 백엔드는 서버의 데이터를 다루고, AI/Data는 데이터를 분석하고 예측하는 것을 좋아해.

- 프론트엔드 추천 시: `[RECOMMEND: FRONTEND]`
- 백엔드 추천 시: `[RECOMMEND: BACKEND]`
- AI/데이터 추천 시: `[RECOMMEND: AI]`

[예시]
답변: "...그래서 회원님은 시각적 감각이 뛰어나시네요! 화면을 직접 설계하는 프론트엔드 개발자가 천직입니다.
[RECOMMEND: FRONTEND]"
"""

def chat_with_ai(messages):
    # API 키 없을 때 테스트용 시나리오
    if not client:
        last_msg = messages[-1]["content"]
        if "시각" in last_msg or "디자인" in last_msg:
            return "눈에 보이는 걸 만드는 걸 좋아하시는군요! 그렇다면 **프론트엔드 개발자**가 딱이에요. 웹사이트의 얼굴을 만드는 일이죠.\n[RECOMMEND: FRONTEND]"
        elif "논리" in last_msg or "데이터" in last_msg:
            return "복잡한 데이터를 다루는 걸 즐기시는군요! 보이지 않는 곳에서 시스템을 움직이는 **백엔드 개발자**가 잘 어울려요.\n[RECOMMEND: BACKEND]"
        else:
            return "어떤 스타일을 선호하시나요? 1. 눈에 보이는 화면 만들기 2. 복잡한 데이터 처리하기"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *messages
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        return "잠시 연결이 원활하지 않습니다. 다시 시도해주세요."