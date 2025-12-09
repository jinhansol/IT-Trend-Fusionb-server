# 📋 DevHub: Developer Trend Fusion Dashboard

![Project Status](https://img.shields.io/badge/Status-Completed-success?style=flat&logo=git&logoColor=white) ![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=flat) ![License](https://img.shields.io/badge/License-MIT-green?style=flat)

> **"정보의 홍수 속에서, 나에게 필요한 기술만 큐레이션하다."** <br/>
> 사용자의 기술 스택과 관심사를 분석하여 **맞춤형 학습 로드맵**과 **기술 아티클**을 추천해주는 **개인화 대시보드** 서비스입니다.

---

## 1. 📅 프로젝트 개요 (Overview)

| 항목 | 내용 |
| :--- | :--- |
| **프로젝트명** | DevHub (IT Trend Fusion Server) |
| **개발 기간** | 2025.10 ~ 2025.12 |
| **개발 인원** | 1명 (Full Stack) |
| **핵심 의도** | 개발자의 커리어 단계에 맞춰 최적의 학습 경로를 제시하고 개인화된 정보 허브를 구축 |

---

## 2. 🛠️ 기술 스택 (Tech Stack)

| 구분 | 기술 스택 | 선정 이유 |
| :---: | :--- | :--- |
| **Frontend** | ![](https://img.shields.io/badge/React-18-blue?logo=react&logoColor=white) ![](https://img.shields.io/badge/Vite-5-purple?logo=vite&logoColor=white) ![](https://img_shields.io/badge/Tailwind-3-cyan?logo=tailwindcss&logoColor=white) ![](https://img.shields.io/badge/Recharts-2.12-orange) | SPA의 빠른 렌더링, 로드맵/능력치 차트 시각화에 용이 |
| **Backend** | ![](https://img.shields.io/badge/FastAPI-0.100-green?logo=fastapi&logoColor=white) ![](https://img.shields.io/badge/Python-3.9-blue?logo=python&logoColor=white) | 비동기 처리(Async)를 통한 성능 확보 및 크롤링/데이터 처리 활용 |
| **Database** | ![](https://img.shields.io/badge/MariaDB-10.6-brown?logo=mariadb&logoColor=white) ![](https://img.shields.io/badge/SQLAlchemy-2.0-red?logo=sqlalchemy&logoColor=white) | 관계형 데이터의 구조적 저장과 ORM을 통한 유지보수성 향상 |
| **Core** | **JWT, Passlib** | 토큰 기반의 안전한 인증 시스템 구축 |

---

## 3. ✨ 핵심 기능 (Key Features)

### 3.1. 🎯 Personalized Career Roadmap (맞춤형 로드맵)
| 기능 | 설명 |
| :--- | :--- |
| **FE/BE 필터링** | 사용자의 관심사를 기반으로 로드맵을 자동으로 **가지치기(Filtering)**하여 보여줍니다. |
| **Gamification** | **Hexagon Radar Chart**를 통해 스탯을 시각화하고, **미니 퀴즈** 결과에 따라 스탯이 실시간 업데이트됩니다. |
| **UX Flow** | 비로그인 유저는 **AI 진단 후 Personal 맵을 체험판**으로 경험하도록 유도합니다. |

### 3.2. 📰 Dev Trend Fusion
| 기능 | 설명 |
| :--- | :--- |
| **Dev Dashboard** | OKKY, Dev.to 기술 아티클을 수집/분석하여 트렌드 및 이슈를 제공합니다. |
| **인증 통합** | **JWT 토큰 기반 인증**을 통해 로그인 시 로드맵 필터링 및 대시보드 데이터가 즉시 갱신됩니다. |

---

## 4. 💥 트러블 슈팅 및 리팩토링

| Issue | 현상 및 해결 |
| :--- | :--- |
| **Legacy 코드 분리** | 기존 크롤링 코드가 메인 브랜치와 혼재. 👉 **Git Branch** 활용, 구 버전을 `legacy-job-crawling`에 **보존**하고 `main`은 로드맵 기능으로 리팩토링. |
| **데이터 구조 충돌** | 개인화 API와 Public API의 데이터 구조가 달라 프론트엔드 충돌. 👉 **Backend**에서 개인화 API도 Source별로 분류하여 **구조 통일** 및 **Fallback Logic** 구현. |
| **JWT ID 획득 오류** | 프론트엔드에서 유저 ID 획득에 타입 에러 발생. 👉 **Backend**의 토큰 생성 로직에 **`id` 필드를 페이로드에 포함**하여 토큰 디코딩만으로 ID 즉시 획득하도록 개선. |

---

## 5. 🚀 설치 및 실행 (Getting Started)

### Prerequisites

* Docker & Docker Compose
* `requirements.txt` 및 `package.json` 최신화 완료 (Git에 반영됨)

### 실행 명령어

```bash
# 1. Repository Clone
git clone [https://github.com/jinhansol/IT-Trend-Fusionb-server.git](https://github.com/jinhansol/IT-Trend-Fusionb-server.git)

# 2. Environment Setup
# 프로젝트 폴더로 이동 후 backend/.env 파일을 생성하고 DB 정보를 입력하세요.

# 3. Docker Run (Build & Start)
# DB 호스트명 자동 매핑 및 환경변수 설정을 위해 docker-compose 사용
docker-compose up --build -d

# 접속 정보	URL
Frontend	http://localhost:5173
Backend API Docs	http://localhost:8000/docs
```

## 6. 📝 회고 (Retrospective)
이번 프로젝트는 단순한 CRUD를 넘어 **"데이터 수집(Crawling) → 가공(Classification) → 개인화(Personalization)"**로 이어지는 데이터 파이프라인 전체를 경험했습니다. **레거시 코드 처리(Git 브랜치 전략)**와 신규 기능 통합(Full-Stack 데이터 플로우) 과정에서 유지보수성과 API 설계의 중요성을 깊이 체감했습니다. 향후 Redis 캐싱을 도입하여 대시보드 로딩 속도를 개선할 계획입니다.
