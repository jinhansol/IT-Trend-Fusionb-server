# services/tech_dictionary.py

"""
기술 기반 뉴스 분석 사전 (B안)
"""

# ============================================================
# 1) 기술 카테고리 / 키워드 리스트
# ============================================================

TECH_DICTIONARY = {
    "ai": [
        "ai", "machine learning", "deep learning",
        "ml", "llm", "large language model",
        "gpt", "chatgpt", "rag", "bert", "t5",
        "neural network", "computer vision",
        "generative ai", "파인튜닝", "딥러닝",
        "openai", "anthropic", "claude"
    ],

    "frontend": [
        "react", "next", "vue", "svelte",
        "angular", "tailwind", "javascript",
        "typescript", "html", "css", "ui"
    ],

    "backend": [
        "node", "express", "nestjs", "django",
        "flask", "fastapi", "spring", "java",
        "go", "golang", "rust", "serverless",
        "microservice"
    ],

    "mobile": [
        "ios", "swift", "android", "kotlin",
        "react native", "flutter"
    ],

    "data": [
        "big data", "spark", "hadoop", "flink",
        "etl", "elt", "분산처리", "data pipeline"
    ],

    "cloud": [
        "aws", "azure", "gcp", "docker",
        "kubernetes", "k8s", "terraform",
        "github actions", "devops"
    ],

    "security": [
        "cybersecurity", "privacy", "encryption",
        "authentication", "authorization",
        "zero trust", "개인정보", "보안"
    ],
}

# ============================================================
# 2) 불용어 (기술 단어 제외)
# ============================================================

STOPWORDS = [
    "기술", "업계", "기업", "서비스",
    "출시", "발표", "개발", "도입",
    "업데이트", "시장", "관련",
    "효과", "업무", "산업", "분야"
]
