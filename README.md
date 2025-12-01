# 📋 DevHub: Developer Trend Fusion Dashboard

![Project Status](https://img.shields.io/badge/Status-Completed-success?style=flat&logo=git&logoColor=white) ![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=flat) ![License](https://img.shields.io/badge/License-MIT-green?style=flat)

> **"정보의 홍수 속에서, 나에게 필요한 기술만 큐레이션하다."** <br/>
> 사용자의 기술 스택과 관심사를 분석하여 **채용 공고(Career)**와 **기술 아티클(Dev)**을 맞춤 추천해주는 개인화 대시보드 서비스입니다.

<br/>

## 📅 1. 프로젝트 개요 (Overview)
- **프로젝트명:** DevHub (IT Trend Fusion Server)
- **개발 기간:** 2025.10 ~ 2025.12
- **개발 인원:** 1명 (Full Stack)
- **배포 URL:** [배포 링크가 있다면 여기에 입력]
- **기획 의도:**
  개발자에게 필요한 정보는 너무 많고 파편화되어 있습니다. 채용 사이트와 기술 커뮤니티를 일일이 돌아다니는 비효율을 줄이고, **"로그인 한 번으로 내 스택에 맞는 정보만 모아보는"** 허브를 만들고자 했습니다.

<br/>

## 🛠️ 2. 기술 스택 (Tech Stack)

| 구분 | 기술 스택 | 선정 이유 |
|:---:|:---|:---|
| **Frontend** | ![React](https://img.shields.io/badge/React-18-blue?logo=react&logoColor=white) ![Vite](https://img.shields.io/badge/Vite-5-purple?logo=vite&logoColor=white) ![Tailwind](https://img.shields.io/badge/Tailwind-3-cyan?logo=tailwindcss&logoColor=white) | 컴포넌트 재사용성 및 SPA의 빠른 렌더링 속도, 직관적인 UI 개발을 위해 선택 |
| **Backend** | ![FastAPI](https://img.shields.io/badge/FastAPI-0.100-green?logo=fastapi&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.9-blue?logo=python&logoColor=white) | 비동기 처리(Async)를 통한 성능 확보 및 Python의 강력한 크롤링 라이브러리 활용 |
| **Database** | ![MariaDB](https://img.shields.io/badge/MariaDB-10.6-brown?logo=mariadb&logoColor=white) ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?logo=sqlalchemy&logoColor=white) | 관계형 데이터의 구조적 저장과 ORM을 통한 유지보수성 향상 |
<br/>

## ✨ 3. 핵심 기능 (Key Features)

### 3.1. 듀얼 대시보드 (Dual Dashboard)
- **Career Dashboard:** 채용 공고를 분석하여 Frontend/Backend 트렌드를 차트로 시각화하고, 사용자 스택에 맞는 공고를 필터링합니다.
- **Dev Dashboard:** OKKY, Dev.to 등 기술 블로그 글을 수집하여 '트렌딩 토픽'과 '이슈 키워드'를 분석해 제공합니다.

### 3.2. 스마트 관심사 분류 (Smart Categorization)
- 사용자가 선택한 키워드를 **Tech Stack(기술)**과 **Interest Topic(주제)**으로 자동 분류하여 DB에 저장합니다.
- 예: "Python" → Tech Stack, "Startups" → Interest Topic

### 3.3. 실시간 개인화 (Real-time Personalization)
- JWT 토큰 기반의 인증 시스템을 통해 로그인 즉시 개인화 모드로 전환됩니다.
- 관심사 수정 시 `auth-change` 이벤트를 통해 새로고침 없이 대시보드 데이터가 즉시 갱신됩니다.

<br/>

## 💥 4. 트러블 슈팅 (Troubleshooting)

### 🔥 Issue 1: Public vs Personal 데이터 구조 불일치와 Fallback 처리
- **현상:**
  - 비로그인(Public) 상태에서는 데이터를 `OKKY`와 `Dev.to` 탭으로 나누어 보여주었으나, 개인화(Personal) API는 단순히 추천된 글 리스트(`Recommended`) 하나만 반환하도록 설계되어 프론트엔드 구조와 충돌함.
  - 신규 가입자(Cold Start)의 경우 추천 데이터가 없어 화면이 비어 보이는 문제 발생.
- **해결:**
  - **Backend:** `dev_service.py`를 리팩토링하여 Personal API도 검색된 결과를 다시 Source별(`okky`, `devto`)로 분류하여 반환하도록 구조 통일.
  - **Frontend:** 개인화 API 호출 실패 시 또는 데이터가 없을 시, 자동으로 Public API를 호출하는 **Fallback Logic**을 구현하여 UX 단절을 방지함.

### 🔥 Issue 2: 크롤링 데이터의 비정형성 및 중복 문제
- **현상:**
  - `OKKY`와 `Dev.to`의 HTML 구조가 다르고, 특히 날짜 포맷(ISO vs 상대 시간)이나 태그 형식이 제각각이라 DB 저장 시 에러가 다수 발생.
  - 스케줄러가 돌 때마다 이미 수집한 글이 중복으로 쌓이는 문제.
- **해결:**
  - **정규화(Normalization):** 각 사이트별 전처리 함수를 작성하여 날짜와 태그를 통일된 포맷으로 변환 후 저장.
  - **Upsert 구현:** DB 저장 시 `source_id`(원문 ID)를 기준으로 존재 여부를 확인. 이미 있는 글이면 `update`(조회수, 댓글수 갱신), 없으면 `insert` 하는 로직으로 데이터 무결성 확보.

### 🔥 Issue 3: JWT 토큰과 422 Unprocessable Entity
- **현상:** 프론트엔드에서 유저 관심사를 조회할 때 `user_id`가 필요한데, 로그인 직후 토큰에는 이메일(`sub`) 정보만 있어 별도 조회가 필요하거나 타입 에러(422)가 발생.
- **해결:** `user_service.py`의 토큰 생성 로직에 `id` 필드를 페이로드에 포함. 프론트엔드에서 토큰 디코딩만으로 즉시 유저 ID를 획득하여 API 요청 효율성을 높임.

<br/>

## 🚀 5. 설치 및 실행 (Getting Started)

### Prerequisites
- Docker & Docker Compose

```bash
# 1. Repository Clone
git clone [https://github.com/jinhansol/IT-Trend-Fusionb-server.git](https://github.com/jinhansol/IT-Trend-Fusionb-server.git)

# 2. Environment Setup
# backend/.env 파일을 생성하고 DB 정보를 입력하세요.

# 3. Docker Run (Build & Start)
docker-compose up --build -d
```
- **Frontend:** `http://localhost:80`
- **Backend API Docs:** `http://localhost:8000/docs`

<br/>

## 📝 6. 회고 (Retrospective)
이번 프로젝트는 단순한 CRUD를 넘어 **"데이터 수집(Crawling) -> 가공(Classification) -> 개인화(Personalization)"**로 이어지는 데이터 파이프라인 전체를 경험해볼 수 있었습니다. 특히 프론트엔드와 백엔드 간의 데이터 구조 불일치를 해결하는 과정에서 **API 설계의 중요성**을 깊이 체감했습니다. 향후 Redis 캐싱을 도입하여 대시보드 로딩 속도를 개선할 계획입니다.
