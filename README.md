# 📋 DevHub: Developer Trend Fusion Dashboard

![Project Status](https://img.shields.io/badge/Status-Completed-success?style=flat&logo=git&logoColor=white) ![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=flat) ![License](https://img.shields.io/badge/License-MIT-green?style=flat)

> **"정보의 홍수 속에서, 나에게 필요한 기술만 큐레이션하다."** <br/>
> 사용자의 기술 스택과 관심사를 분석하여 **맞춤형 학습 로드맵**과 **기술 아티클**을 추천해주는 **개인화 대시보드** 서비스입니다.

---

## 🚧 DevHub 2.0 개발 환경 (진행 중)

DevHub 2.0은 새 백엔드(`backend/app/`)와 새 MariaDB 스키마로 재구축 중입니다. 학교 파이널 프로젝트의 마지막 상태는 `legacy-final-project` 태그로 보존합니다. 아래 소개(1장 이후)는 기존 버전 기준입니다.

| 구분 | 버전 |
| :--- | :--- |
| Python | 3.12 (`backend/.python-version`), 의존성 관리: [uv](https://docs.astral.sh/uv/) |
| Node.js | 24 LTS (`.nvmrc`) |
| MariaDB | 11.4.13 LTS (Docker Compose) |

### 1) MariaDB 실행

```bash
docker compose up -d --wait mariadb
```

- `127.0.0.1:3307`에 개발 DB `devhub_dev`와 테스트 DB `devhub_test`가 계정이 분리된 상태로 생성됩니다. 테스트 계정은 개발 DB에 접근할 수 없습니다.
- 초기화 스크립트(`docker/mariadb/init/`)는 데이터 볼륨이 처음 만들어질 때 한 번만 실행됩니다.
- 기본 비밀번호는 로컬 전용입니다. 바꾸려면 루트의 `.env.example`을 `.env`로 복사해 수정하세요.
- `docker compose down -v`는 로컬 DB 데이터를 삭제하므로 주의하세요.

### 2) 백엔드

```bash
cd backend
cp .env.example .env          # 이미 .env가 있다면 DATABASE_URL, TEST_DATABASE_URL, JWT_SECRET 줄만 추가
uv sync
uv run alembic upgrade head   # 스키마는 Alembic으로만 관리합니다
uv run uvicorn app.main:create_app --factory --reload
```

- 헬스체크: `GET http://127.0.0.1:8000/api/health` (프로세스), `GET /api/health/ready` (DB 연결)
- API 문서(로컬만): `http://127.0.0.1:8000/api/docs`
- 기존 백엔드(`backend/main.py`)는 별도 실행 경로이며 새 앱과 섞이지 않습니다.
- 인증 API: `POST /api/auth/register`, `/login`, `/refresh`, `/logout`, `GET /api/me`. access token은 응답 본문(브라우저 메모리), refresh token은 httpOnly 쿠키(`/api/auth` 경로 전용)로 전달됩니다.

### 학습 콘텐츠

학습 트랙은 `backend/content/<트랙>/`에 파일로 관리합니다. `track.yaml`에 트랙 정보를, `units/`에 단원마다 파일 하나를 둡니다. 새 트랙을 추가할 때 코드는 바꾸지 않습니다.

```bash
cd backend
uv run python -m app.content_loader load content/python --dry-run   # 바뀔 내용만 확인
uv run python -m app.content_loader load content/python             # DB에 반영
```

- 같은 파일을 여러 번 반영해도 결과가 같습니다. 파일에서 지운 단원·활동은 삭제되지 않고 `retired`(비공개) 처리됩니다.
- 형식 오류(중복 slug·순서, 필수 항목 누락, http(s)가 아닌 링크, 렌더링되지 않는 굵게 표시 등)가 있으면 아무것도 반영하지 않습니다.
- 이미지·동영상은 저장소에 넣지 않고 외부 링크로 연결합니다.
- 단원 파일의 `quiz:`에 문항과 정답·해설을 적습니다(문항 1~30개, 기본 통과 기준 80%). 퀴즈가 없는 단원은 완료할 수 없습니다. 이미 응시 기록이 있는 퀴즈를 고치면 새 버전이 만들어지고, 이미 완료한 단원은 완료 상태가 유지됩니다.

### 학습 진행·보상 규칙

- 단원 완료 = 필수 활동을 모두 "학습 완료로 표시" + 단원 퀴즈 통과(순서 무관). 완료는 취소되지 않습니다.
- XP는 단원 완료 때만 100 XP 지급되며, 같은 단원으로 두 번 받지 않습니다. 레벨은 XP 합계로 계산합니다(1→2레벨 100 XP, 이후 레벨마다 필요 XP +50). 값은 `XP_PER_UNIT_COMPLETION`, `LEVEL_BASE_XP`, `LEVEL_STEP_XP`로 바꿀 수 있습니다.
- 퀴즈 재도전은 무제한이며, 통과 전에는 점수와 틀린 문항 번호만, 통과 후에는 정답과 해설을 보여줍니다. 채점은 서버에서 하고 정답은 공개 API에 포함되지 않습니다.
- 개인 진행 API는 `/api/me/...` 아래에 있고 로그인한 사용자 자신의 기록만 다룹니다.

### 3) 테스트

```bash
cd backend
uv run pytest                        # 단위 + MariaDB 통합 테스트 (TEST_DATABASE_URL 필요)
uv run pytest -m "not integration"   # DB 없이 단위 테스트만
uv run ruff check && uv run ruff format --check
```

통합 테스트는 실제 연결된 DB 이름이 `*_test`인지 확인한 뒤에만 실행되며, `TEST_DATABASE_URL`이 없으면 건너뛰지 않고 실패합니다.

E2E 테스트(Playwright)는 실제 브라우저로 회원가입 → 단원 학습 → 퀴즈 재도전·통과 → XP 확인 → 새로고침·재로그인 흐름을 검사합니다. 테스트 DB(`devhub_test`)에 마이그레이션과 콘텐츠를 반영한 뒤 API(8100)와 Vite(5180)를 직접 띄웁니다. 백엔드 pytest와 동시에 실행하지 마세요.

```bash
cd frontend && npm ci && cd ../e2e
npm ci
npx playwright install chromium   # 처음 한 번
npx playwright test
```

### 4) 프론트엔드

```bash
cd frontend
npm ci
npm run dev       # /api 요청은 Vite proxy로 새 백엔드(127.0.0.1:8000)에 전달
npm test          # Vitest
npm run build
```

새 API 호출은 `src/api/client.js`를 사용합니다. 로그인 상태는 `src/auth/AuthProvider.jsx`가 관리하며, 토큰을 localStorage에 저장하지 않습니다. 브라우저는 반드시 Vite 개발 서버(`http://localhost:5173`)로 접속해야 refresh 쿠키가 같은 출처로 동작합니다.

전환 기간 안내: 기존 화면(Home·Dev·Career)의 API 모듈은 아직 옛 백엔드 주소(`localhost:8000`)를 직접 호출합니다. 새 백엔드를 8000에서 실행하면 기존 화면은 데이터를 불러오지 못합니다. 옛 화면을 함께 확인하려면 새 백엔드를 다른 포트(예: `--port 8001`)로 띄우고 `frontend/.env.local`에 `VITE_DEV_API_PROXY_TARGET=http://127.0.0.1:8001`을 지정하세요. 옛 화면은 옛 DB의 사용자 기준이라 새 로그인과 연결되지 않습니다.

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
