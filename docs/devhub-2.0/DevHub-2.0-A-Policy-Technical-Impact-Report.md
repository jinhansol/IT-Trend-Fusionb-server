# DevHub 2.0 — A안(사용자 상태·개인화) 기술 영향 감사 보고서

| 항목 | 내용 |
| :--- | :--- |
| 작성일 | 2026-10-28 |
| 기준 | `main` `927cc4a` + Phase 5 미커밋 변경(작업 트리) |
| 작업 범위 | 읽기 전용 감사. 코드·DB·마이그레이션·의존성 변경, 커밋, push 없음. 이 보고서 파일만 새로 작성 |
| 근거 표기 | **[확인]** 실행·조회로 확인 / **[정적]** 코드·모델·설정을 읽고 판단 / **[추정]** 실데이터·운영 환경에 대한 예상 |
| 제외 | 네트워크(ProxyError) 해결 |

검증 기준선 [확인]: 이 세션의 최근 실행 기준으로 백엔드 pytest 203 passed, 프론트 Vitest 29 passed, Playwright E2E 3 passed입니다.

---

## 1. 핵심 결론

1. **A안은 현재 구조와 근본적으로 충돌하지 않습니다.** 덧붙이는 방식(새 테이블, 새 API, 선택 필드)으로 구현할 수 있습니다.
   - 공개 콘텐츠·학습 정의와 회원 전용 기록은 이미 API 경로 단위로 분리되어 있습니다(`/api/tracks`, `/api/news` 등 공개 / `/api/me/...` 로그인 필수).
   - 기록 테이블은 모두 토큰의 사용자 ID로만 접근합니다. [정적] + [확인] 격리 테스트
2. **가장 중요한 충돌은 이름입니다. `users.role`은 이미 권한 역할(`user`/`admin`)로 쓰이고 있습니다.** [정적]
   - 근거: `backend/app/models/user.py` `USER_ROLES`, CHECK 제약 `role_valid`, `/api/me` 응답의 `role`
   - A안의 "입문자/개발자/탐색 중"을 같은 컬럼이나 같은 이름(`role`)에 넣으면 권한 체계와 섞입니다. **별도 필드(예: `learner_type`)가 필수입니다.**
3. **개인화 OFF 정책을 지금 위반하는 코드는 없습니다.** 개인화 데이터 자체가 아직 없기 때문입니다. [정적]
   - `user_settings.personalization_enabled`는 있지만 어떤 기능도 읽지 않습니다.
   - 위험은 앞으로 생깁니다. 관심 기술을 읽는 코드가 여러 서비스에 흩어지면 OFF 검사가 빠질 수 있습니다. **개인화 데이터를 읽는 모듈을 하나로 제한하는 경계가 필요합니다.**
4. **Home·Dev 개인화의 최소 구조**
   - 기존 목록 API(최신순·수동 필터)는 그대로 둡니다.
   - 로그인·개인화 ON 전용 "추천" API를 따로 추가합니다(개수 제한, 추천 이유 포함).
   - 이렇게 하면 다음이 함께 해결됩니다: 기존 API 하위 호환, OFF 시 순위 불변, offset 페이지네이션과 개인화 정렬의 충돌.
5. **구조적 결함 3가지**
   - "로그인했으면 사용, 아니면 게스트"를 처리하는 선택적 인증 의존성이 없습니다(`app/api/deps.py`에는 `get_current_user`만 있음).
   - Career 학습 단원·트랙에 기술 ID 연결이 없습니다.
   - 기술 태깅이 단어 일치라 오탐이 추천 이유에 그대로 드러납니다. [확인] 사례 점검: "컨테이너선"이 Docker로 태깅됨
6. **Career 게스트 체험**
   - 학습 콘텐츠 열람: 지금도 가능합니다. [확인] E2E의 비로그인 단계
   - 퀴즈 체험: 현재 불가능합니다. 채점 API가 로그인 필수이고 응시를 DB에 기록합니다. 기록하지 않는 채점 경로를 추가하면 가능합니다.
   - AI 나침반 게스트 허용: 비용·남용 방지 설계가 먼저입니다. 현재는 로그인 실패 제한기(프로세스 메모리 기반)만 있고, **회원가입에는 횟수 제한이 없습니다.** [정적]

---

## 2. A안과 현재 코드의 적합성

| A안 요구 | 현재 상태 | 적합성 | 근거 |
| :--- | :--- | :--- | :--- |
| 게스트: Home 뉴스 탐색 | 공개 API `GET /api/news`, 인증 없음 | **충족** | [정적] `app/api/routes/content.py` / [확인] E2E `feeds.spec.js` |
| 게스트: Dev 콘텐츠 탐색 | 공개 `GET /api/dev/channels`, `/posts` | **충족** | 동일 |
| 게스트: Dev "기초 자료" 탐색 | 기초 자료(개념 문서·학습 자료) 데이터 없음 | **미충족** (데이터 필요) | [정적] 관련 테이블 없음 |
| 게스트: Career 기초 학습 | 트랙·단원·활동 공개 열람 가능, 퀴즈는 로그인 필요 | **부분 충족** | [정적] `UnitPage.jsx` `loggedIn && detail`일 때만 `QuizPanel` |
| 게스트: 진로 탐색·AI 나침반 체험 | 없음 (v1 `AICompassModal`은 라우팅 제외, 옛 백엔드용) | **미충족** | [정적] |
| 게스트: 기록·XP 저장 없음 | 기록 API 전부 `get_current_user` 필수 | **충족** | [정적] `me_learning.py` 5개 라우트 / [확인] `test_personal_endpoints_require_login` |
| 회원가입 시 역할 선택 | `RegisterRequest`에 해당 필드 없음, `users.role`은 권한용 | **미충족 + 이름 충돌** | [정적] `schemas/auth.py`, `models/user.py` |
| 역할은 안내·메뉴에만, 추천 순위 미반영 | 추천 자체가 없음 | 정책 위반 없음 (향후 강제 필요) | [정적] |
| 회원: 학습 기록·퀴즈·XP·이어보기 | 구현 완료 | **충족** | [확인] Phase 4 테스트·E2E |
| 개인화 기본 OFF | `UserSettings.personalization_enabled` 기본 False, 가입 시 행 생성 | **충족** (저장만, 사용처 없음) | [정적] `services/auth.py` `register_user` |
| 개인화 명시적 활성화 | 설정 변경 API 없음 (`GET /api/me`만 값 노출) | **미충족** | [정적] `routes/me.py` |
| 관심 기술·목표·역량 | 테이블 없음 (설계 문서 후보만) | **미충족** | [정적] |
| Home·Dev 우선순위 개인화 + 근거 설명 | 없음 | **미충족** | [정적] |
| 전체 콘텐츠 탐색 유지 | 기존 목록 API가 개인화와 무관 | **충족 가능** (분리 구조 유지 시) | [정적] |
| OFF·초기화·목표 변경 시 학습 기록 보존 | 학습 기록 테이블은 개인화 데이터와 FK 관계 없음 | **충족 가능** | [정적] `models/progress.py`, `models/quiz.py` |

---

## 3. 기존 기능 재사용 가능성

| 재사용 대상 | 위치 | A안에서의 용도 |
| :--- | :--- | :--- |
| 인증·토큰 회전, 사용자 격리 패턴 | `app/core/security.py`, `services/auth.py`, `deps.get_current_user` | 회원·개인화 회원 식별. 경로·본문에서 사용자 ID를 받지 않는 원칙을 그대로 적용 |
| `UserSettings` 1:1 행 (가입 시 생성) | `models/user.py` | 개인화 ON/OFF 저장소. 역할 저장 후보 중 하나(6절) |
| 공개/회원 API 분리 | `routes/learning.py`·`content.py` vs `routes/me.py`·`me_learning.py` | 게스트=공개, 회원=`/api/me/...` 구조 유지 |
| 학습 진행·XP 서비스 | `services/learning_progress.py`, `services/rewards.py` | 변경 없이 유지. 개인화 추천은 이 결과를 읽기만 |
| 기술 분류 57개 + 콘텐츠-기술 연결 | `models/content.py` `Technology`, `ContentTechnology` | 관심 기술 ID, 추천 근거 |
| 기술 필터 쿼리 | `services/content_feed.py` `_with_technology` | 추천 후보 조회(여러 기술로 확장) |
| 파일 + 멱등 로더 패턴 | `app/content_loader/` | 단원-기술 연결, 기초 자료 목록 관리 |
| 실패 제한기 | `services/rate_limit.py` `FailedAttemptLimiter` | 게스트 체험·AI 호출 제한의 개념 재사용 (단, 프로세스별 메모리라 확장 시 공유 저장소 필요 — 파일 주석에 명시) |
| 프론트 인증 상태 | `auth/AuthProvider.jsx` (`loading`/`anonymous`/`authenticated`), `hooks/useMyResource.js` | 상태별 화면 분기, 로그인 전환 시 개인 데이터 재조회 |
| 로그인 안내 | `components/learn/LoginPrompt.jsx` | 게스트 → 회원 전환 지점 |

---

## 4. 정책 충돌 및 구조적 결함

### 4-1. 충돌·결함 목록

| # | 문제 | 유형 | 영향 | 근거 |
| ---: | :--- | :--- | :--- | :--- |
| 1 | `users.role`(권한)과 A안 "역할"(학습자 유형)의 이름·의미 충돌 | 정책 충돌 | 같은 컬럼 사용 시 CHECK 위반 또는 권한 판정 오염. `/api/me`가 이미 `role: "user"`를 반환하므로 프론트에서도 혼동 | [정적] `models/user.py` `USER_ROLES`, `schemas/user.py` `UserPublic.role` |
| 2 | 선택적 인증 의존성 없음 | 구조 결함 | 공개 API에서 로그인 여부에 따라 응답을 바꿀 수 없음 | [정적] `api/deps.py` |
| 3 | 프론트는 로그인 중이면 **모든 요청**(공개 API 포함)에 `Authorization`을 붙임 | 설계 주의 | 선택적 인증을 추가할 때 "만료 토큰"을 게스트로 처리하면 개인화가 조용히 꺼지고, 401로 처리하면 공개 API에서도 토큰 갱신이 일어남. 처리 규칙을 정해야 함 | [정적] `api/client.js` 요청 인터셉터 |
| 4 | Home·Dev가 로그인 상태 변화에 반응하지 않음 | 구조 결함(개인화 도입 시) | 로그인·로그아웃 후 목록이 그대로 | [정적] `HomePage.jsx`, `DevPage.jsx`, `usePagedList.js`가 `useAuth` 미사용 |
| 5 | 초기 로딩 시 인증 확인(`loading`) 전에 공개 요청이 먼저 나감 | 설계 주의 | 개인화 영역이 게스트 결과로 먼저 그려졌다가 바뀜 | [정적] `AuthProvider.jsx` 초기 `status: "loading"` |
| 6 | offset 페이지네이션 | 구조 결함(정렬 개인화 시) | 수집 중이거나 순위가 바뀌면 "더 보기"에서 중복·누락 | [정적] `content_feed._page` |
| 7 | 학습 단원·트랙에 기술 연결 없음 | 데이터 결함 | 관심 기술 → 단원, 목표 → 단원 추천 불가 | [정적] `models/learning.py`, `content_loader/schema.py` `UnitDef` |
| 8 | 단원 난이도·세부 주제 없음 | 데이터 결함 | 입문자/개발자 안내, 역량 기반 제안에 쓸 기준이 없음 | [정적] `LearningUnit` 컬럼 |
| 9 | 태깅 신뢰도·근거 위치 없음, 단어 일치 오탐 | 데이터 품질 | 추천 이유("관심 기술 Docker")가 틀린 기사에 표시됨 | [확인] 사례 점검(Phase 5 분석 보고서 4-3) |
| 10 | 개인화 설정 변경 API 없음 | 기능 공백 | ON/OFF·초기화 불가 | [정적] `routes/me.py` |
| 11 | 회원가입 횟수 제한 없음 | 보안·남용 | 회원 단위 AI 한도를 계정 대량 생성으로 우회 가능 | [정적] `routes/auth.py` `register` (`login`만 `login_limiter` 사용) |
| 12 | 실패 제한기가 프로세스 메모리 기반 | 운영 제약 | 워커 여러 개·재시작 시 한도가 공유·유지되지 않음 | [정적] `rate_limit.py` 모듈 주석 |
| 13 | 개인화 응답의 캐시 정책 없음 | 향후 위험 | CDN·프록시를 두면 사용자별 응답이 공유될 수 있음 | [정적] 캐시 헤더 설정 없음 / [추정] 배포 구성에 따라 |
| 14 | 실데이터 미수집 | 데이터 품질 | 추천 품질 평가 불가 | [확인] 개발 DB `contents` 0건 |

### 4-2. 개인화 OFF 정책 위반 가능 지점 (현재와 미래)

**현재 [정적]:** 위반 없음. 개인화 데이터를 읽는 코드가 없습니다.

**향후 위험 지점**

- `content_feed.list_news` / `list_channel_posts`에 관심 기술 정렬을 직접 넣는 경우
  - OFF 확인이 빠질 수 있고, 기존 공개 API의 순서가 바뀝니다.
- Career `summary`(`learning_progress.summary`)의 `continue_unit`에 목표 기반 선택을 섞는 경우
  - 이어보기는 일반 회원 기능이므로 OFF에서도 기존 규칙(최근 활동 단원)이 유지되어야 합니다.
- 회원가입 역할을 추천 정렬에 쓰는 경우
  - A안 위반입니다. 역할 값은 안내·메뉴 계층에서만 읽도록 제한해야 합니다.

---

## 5. 사용자 상태별 API·화면 변경 범위

### 5-1. API

| API | 게스트 | 회원(OFF) | 회원(ON) | 변경 |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/news`, `/api/dev/channels`, `/api/dev/channels/{c}/posts`, `/api/trends`, `/api/feed-status` | ○ | ○ (동일 응답) | ○ (동일 응답) | **변경 없음 권장** (수동 탐색·필터 전용으로 고정) |
| `GET /api/tracks...`, `GET .../quiz` | ○ | ○ | ○ | 선택 필드 추가 가능(단원 기술·난이도) |
| `POST /api/auth/register` | 가입 | – | – | 선택 필드 `learner_type` 추가 (기존 클라이언트 호환) + 가입 횟수 제한 검토 |
| `GET /api/me` | 401 | ○ | ○ | 응답에 `settings.learner_type` 등 추가 (`role`은 의미 유지) |
| 신규 `PATCH /api/me/settings` | 401 | 역할 변경, 개인화 켜기 | 끄기 | **신규** |
| 신규 `PUT /api/me/interests`, `/goals`, `/skills` | 401 | 정책 결정 필요 (OFF에서 입력 허용 여부) | ○ | **신규** |
| 신규 `POST /api/me/personalization/reset` | 401 | – | ○ | **신규**, 학습 기록 테이블은 건드리지 않음 |
| 신규 `GET /api/me/recommendations?scope=news\|dev\|career` | 401 | 빈 결과 + `personalization: "off"` 또는 403 (정책 결정) | 추천 + 이유 | **신규** |
| `/api/me/summary`·진행·퀴즈 API | 401 | ○ | ○ | **변경 없음** |
| 신규 게스트 체험 채점 (예: `POST /api/tracks/{t}/units/{u}/quiz/check`) | ○ (기록 없음) | 선택 | 선택 | **신규·선택** (8절) |

### 5-2. 화면

| 화면 | 게스트 | 회원(OFF) | 회원(ON) | 변경 파일 후보 |
| :--- | :--- | :--- | :--- | :--- |
| Home | 현재 그대로 | + 역할별 시작 안내(선택) | + "나를 위한 뉴스" 영역(추천 API) + 이유 표시. 전체 목록은 아래 그대로 | `pages/home/HomePage.jsx`, 신규 `components/feed/RecommendedSection.jsx` |
| Dev | 현재 그대로 + 기초 자료(데이터 필요) | + 역할별 탐색 메뉴 | + 추천 영역 | `pages/dev/DevPage.jsx` |
| Career 첫 화면 | 로그인 안내 + 트랙 | 내 학습 현황 + 역할별 시작 안내 | + "나의 방향"(목표 기반 제안) | `pages/career/CareerHomePage.jsx` |
| 단원 | 열람 + (선택) 퀴즈 체험 | 현재 그대로 | 현재 그대로 | `pages/career/UnitPage.jsx`, `components/learn/QuizPanel.jsx` |
| 가입 | – | 역할 선택(선택 입력) | – | `modals/SignupPopup.jsx`, `api/auth.js` |
| 설정 | – | 개인화 켜기, 역할 변경 | 관심 기술·목표·역량, 끄기, 초기화 | 신규 `pages/settings/...` |
| 공통 | – | – | – | `HeaderNav.jsx`(설정 진입) |

**로그인 전환 처리:** 개인 영역은 Career의 `useMyResource` 패턴(인증 상태를 의존성에 포함)을 재사용하면 됩니다. 공개 목록은 인증 상태와 무관하게 유지해 불필요한 재조회를 피합니다.

---

## 6. DB·스키마 변경 후보

모두 **추가(additive)** 변경입니다. 기존 테이블 컬럼의 삭제·의미 변경은 없습니다.

### 6-1. 필수 (A안 핵심 기능에 필요)

| 후보 | 구조 | 목적 | 비고 |
| :--- | :--- | :--- | :--- |
| 학습자 유형 | ⓐ `user_settings.learner_type` VARCHAR NULL + CHECK(beginner/developer/exploring), 또는 ⓑ 새 `user_profiles`(user_id PK) | 가입 시 역할 | **`users.role` 사용 금지.** ⓐ가 최소 변경(가입 시 행이 이미 생성됨) |
| `user_interests` | PK(user_id, technology_id), created_at, FK CASCADE(user)·RESTRICT(technology) | 관심 기술 | 중복은 PK로 방지, 멱등 저장 |
| `learning_goals` | id, user_id, title, track_id NULL, technology_id NULL, status(active/archived/completed), created_at, archived_at | 학습 목표 | 초기화·변경 시 삭제 대신 `archived` (설계 문서 4-5 방향) |
| `user_skill_assessments` | PK(user_id, technology_id), self_level CHECK, assessed_at | 현재 역량(자기 평가) | XP와 무관 (확정 원칙) |
| `learning_unit_technologies` | PK(unit_id, technology_id), relation(primary/related) | 관심·목표 → 단원 | 단원 YAML `technologies:`로 관리, 로더가 동기화 |

### 6-2. 선택 (품질·확장)

| 후보 | 목적 |
| :--- | :--- |
| `learning_units.level` (NULL 허용) | 입문자/개발자 안내, 역량 기반 제안 |
| `technology_resources` (technology_id, kind, url, title, language) — YAML 관리 | Dev "기초 자료", 공식 문서 연결 |
| `content_technologies.confidence` 또는 `source`(title/excerpt/tag) | 추천 근거 품질, 태그 기반 일치만 추천에 사용하는 등 |
| `technologies.parent_id` 또는 관계 테이블 | React → frontend 같은 상위 분야 추천 |
| `user_settings.personalization_changed_at` | 감사·지원용 |
| 게스트·AI 사용량 테이블 (`usage_quotas` 등) | AI 나침반 남용 방지 (공유 저장소 기반 한도) |

### 6-3. 마이그레이션·정합성 위험

| 위험 | 대응 |
| :--- | :--- |
| MariaDB DDL은 트랜잭션이 안 됨 → 중간 실패 시 일부만 적용 | 기존 규칙 유지: 다운그레이드는 테이블 삭제만, 리비전은 작게 나눔 [정적] 0004·0005 패턴 |
| 기존 사용자의 새 컬럼 값 | `learner_type` NULL = "선택 안 함"으로 정의, 별도 백필 불필요 |
| 기술 삭제 시 연결 깨짐 | 기술은 retire만 하고 삭제하지 않음(현 로더 정책), FK RESTRICT 유지 |
| 개인화 초기화가 학습 기록을 지움 | 개인화 테이블과 학습 기록 테이블 사이에 FK·CASCADE를 두지 않음. 초기화는 개인화 테이블만 대상으로 함 |
| 동시 수정 (탭 두 개에서 관심 기술 저장) | PK 기반 upsert, 전체 교체 API는 한 트랜잭션 |
| 계정 삭제 | 개인화 테이블 FK `ON DELETE CASCADE` (기존 사용자 테이블들과 동일) |

---

## 7. 추천 시스템 최소 구현 구조

**원칙:** 거대한 추천 엔진이 아니라, 설명 가능한 규칙 기반 점수로 시작합니다. 기존 목록 API와 분리합니다.

### 7-1. 모듈 경계 (제안)

```
app/services/personalization.py   유일하게 개인화 데이터(관심·목표·역량·ON/OFF)를 읽는 모듈
    resolve_context(db, user) -> PersonalizationContext
        mode: "guest" | "off" | "on"
        interests, goals, skills (mode == "on"일 때만 채움)
app/services/recommendations.py   context를 받아 후보 조회 → 점수 → 이유 생성
    recommend_content(db, ctx, scope, limit)
    recommend_units(db, ctx, limit)
app/api/routes/me_recommendations.py   GET /api/me/recommendations
```

- 다른 서비스(`content_feed`, `learning_progress`)는 개인화 모듈을 import하지 않습니다.
- 이 규칙은 테스트로 강제할 수 있습니다. 기존 `tests/unit/test_app_startup.py`가 import를 검사하는 방식과 같습니다.
- OFF·게스트일 때 `resolve_context`는 개인화 데이터를 조회하지 않습니다.

### 7-2. 초기 규칙 (예시, 수치는 미확정)

- 후보: 최근 N일 콘텐츠 중 관심 기술 태그가 있는 것
  - 기존 `_with_technology`를 여러 기술로 확장
- 점수: 관심 기술 일치 수, 목표 연관 기술, 최신성, (Dev) 소스 지표의 소스 내 순위
- 결과 개수를 제한합니다(예: 10개). 무한 페이지를 두지 않아 페이지네이션 충돌을 피합니다.
- Career: 목표 기술 ∩ `learning_unit_technologies` - 완료 단원 → 다음 단원 제안

### 7-3. 응답 계약 (제안)

```json
{
  "personalization": "on",
  "items": [
    {
      "content": { "...": "기존 ContentItem 그대로" },
      "reasons": [
        { "type": "interest_technology", "technology": { "slug": "python", "name": "Python" } },
        { "type": "goal", "goal": { "id": 3, "title": "백엔드 취업 준비" } }
      ]
    }
  ]
}
```

- `personalization: "off"`이면 `items: []`를 반환합니다. 403으로 할지는 결정이 필요합니다.
- 이유 `type`은 고정 목록입니다(`interest_technology`, `goal`, `skill_gap`, `next_unit`). 자유 문장이 아니므로 테스트로 검증할 수 있습니다.

### 7-4. 구현 가능성

- 현재 구조로 가능합니다: 기술 ID, 콘텐츠-기술 연결, 학습 진행 조회
- 선행 조건: Phase 6 테이블, 단원-기술 연결, 선택적·필수 인증 정리
- 품질 제약: 태깅 정확도. 초기에는 태그 기반 일치(소스가 준 태그)나 제목 일치만 추천 근거로 쓰는 방안이 있습니다(결정 필요).

---

## 8. Career 게스트 체험 가능성

| 체험 | 현재 | 구현 방법 | 위험 |
| :--- | :--- | :--- | :--- |
| 트랙·단원·활동 열람 | **가능** [확인] | – | – |
| 활동 "학습 완료" 표시 | 불가 (로그인 필수, DB 기록) | 게스트는 버튼 숨김(현재) 또는 브라우저에만 임시 표시 | 브라우저 저장을 쓰면 가입 시 이전 여부를 정해야 함. A안은 "계정 기반 저장 없음"만 명시 |
| 퀴즈 체험 | 불가 (`QuizPanel`은 로그인 시에만, `POST /api/me/quizzes/.../attempts` 로그인 필수) | 기록 없는 채점 API(점수·틀린 문항만, 정답 비공개) | 정답이 이미 공개 저장소에 있어 유출 영향은 낮음(결정 D). 남용(대량 호출) 제한은 필요 |
| 진로 탐색 (정적) | 없음 | 역할별 추천 트랙 안내 같은 정적 콘텐츠 | 낮음 |
| AI 나침반 | 없음 | Phase 6 별도 개발 | **비용·남용** (아래) |

**AI 나침반 게스트 허용 시 필요 사항** [정적·추정]

- 확정 방향은 "로그인 필수"였습니다(Phase 4 계획 0절). 게스트 허용은 이 결정을 바꾸는 것이라 사용자 확정이 필요합니다.
- 필요한 장치
  - IP·기기 단위 일일 한도를 공유 저장소(DB 등)에 둡니다. 현재 메모리 제한기로는 부족합니다.
  - 전체 일일 비용 상한
  - 입력 길이 제한
  - 회원가입 횟수 제한(계정 생성으로 한도 우회 방지)
  - 결과 저장 없음(게스트)
- 기존 퀴즈·XP·진행률은 게스트 기능과 테이블을 공유하지 않으므로 영향이 없습니다. [정적]

---

## 9. 테스트 및 검증 전략

### 9-1. 상태별 시나리오

| 상태 | 검증 항목 |
| :--- | :--- |
| 게스트 | 공개 API 200 / `/api/me/*` 전부 401 / 추천 API 401 / (도입 시) 퀴즈 체험 채점이 DB에 행을 만들지 않음 / 게스트 AI 한도 초과 시 거절 |
| 회원 OFF | 공개 목록 응답이 게스트와 **완전히 동일**(같은 데이터에서 순서·항목 일치) / 추천 API가 개인화 데이터를 읽지 않음(쿼리 감시 또는 모듈 호출 검사) / 학습자 유형을 바꿔도 목록 순서 동일 / 학습 기록·XP 정상 |
| 회원 ON | 추천 결과의 모든 항목이 이유를 가짐 / 이유의 기술이 실제 콘텐츠 태그·관심 기술과 일치 / 전체 목록 API는 여전히 동일 순서 |
| 상태 전환 | 학습자 유형 변경 전후 `user_activity_records`·`quiz_attempts`·`user_unit_progress`·`xp_ledger` 행 수·값 동일 / 개인화 ON→OFF→ON, 초기화 후 학습 기록 동일 / 목표 변경 시 이전 목표 `archived` |
| 권한 | 다른 사용자의 관심·목표·추천을 조회·수정 불가(경로·본문에 사용자 ID 없음) / 비활성 사용자 차단(기존 `test_disabled_user_cannot_login_refresh_or_call_api` 확장) |
| 프론트 | 로그인·로그아웃 시 개인 영역 재조회, 공개 목록 유지 / 인증 확인 중(`loading`)에는 개인 영역을 그리지 않음 / OFF 사용자에게 추천 영역 미표시 |
| E2E | 게스트 탐색 → 가입(역할 선택) → OFF 상태 목록 동일 → 개인화 켜기 → 추천 이유 표시 → 초기화 → 학습 기록·XP 유지 |

### 9-2. 회귀 범위

| 단계 | 기존 테스트 |
| :--- | :--- |
| Phase 2 | `tests/integration/test_auth.py` (가입 필드 추가 영향) |
| Phase 3 | `test_learning_api.py`, `test_content_loader.py` (단원 YAML 확장 영향) |
| Phase 4 | `test_learning_progress.py` 전체 (기록 보존), `e2e/tests/learning.spec.js` |
| Phase 5 | `test_content_api.py`의 `test_read_endpoints_never_write`(공개 API 무쓰기 유지), `test_collector.py`, `e2e/tests/feeds.spec.js` |
| 공통 | `tests/unit/test_app_startup.py` (import 부작용·모듈 경계) |

---

## 10. 구현 단계·의존성·우선순위 (제안)

| 단계 | 내용 | 선행 조건 | 위험 |
| :--- | :--- | :--- | :--- |
| S0 | Phase 5 정리·커밋(트렌드 차트 결정 포함) | 사용자 결정 | 낮음 |
| S1 | 학습자 유형(`learner_type`) + 가입 선택 입력 + `PATCH /api/me/settings`(유형·ON/OFF) + 가입 횟수 제한 | S0 | 낮음 (추가 변경) |
| S2 | 선택적 인증 의존성 규칙, `personalization.resolve_context`, 모듈 경계 테스트 | S1 | 중간 (토큰 만료 처리 규칙) |
| S3 | Phase 6 테이블(관심·목표·역량) + 입력·초기화 API + 설정 화면 | S2 | 중간 (정책 미정 항목 다수) |
| S4 | 단원-기술 연결(+선택: 단원 난이도) | 독립 (S3와 병행 가능) | 낮음 |
| S5 | 추천 API(Home·Dev·Career) + 이유 + 추천 영역 화면 | S3, S4, 실데이터 수집 | 중간 (태깅 품질) |
| S6 | Career 게스트 체험(기록 없는 채점) | 정책 결정 | 낮음 |
| S7 | AI 나침반 | AI 서비스·한도·게스트 정책 결정 | 높음 (비용·남용·환각) |

**의존성 요약**

- 추천(S5)은 개인화 데이터(S3), 단원-기술 연결(S4), 실수집 데이터가 모두 있어야 의미가 있습니다.
- 학습자 유형(S1)은 독립적이라 가장 먼저 할 수 있습니다.

---

## 11. Work 분석에서 추가 검토해야 할 쟁점

이번 감사에서 결론을 내리지 못했거나, 별도 분석(Work 단계)이 필요한 항목입니다.

1. **선택적 인증의 토큰 처리 규칙**
   - 공개 API에 만료 토큰이 오면 401(갱신 유도)로 할지, 게스트로 처리할지
   - 현재 프론트는 모든 요청에 토큰을 붙이므로 두 방식의 사용자 경험·부하 차이 분석
2. **추천 영역과 전체 목록의 중복 노출 처리**: 같은 기사가 추천과 목록에 동시에 나오는 경우
3. **태깅 품질 측정 방법**: 실데이터 수집 후 소스별 표본 검수 기준, 추천에 쓸 최소 품질선
4. **커서 기반 페이지네이션 전환 필요성**: 추천을 분리하면 기존 목록에는 필수 아님. 수집 주기와 함께 재검토
5. **게스트 한도 저장소 선택**: DB 테이블 / 외부 저장소. 배포 구성(Phase 8)과 연동
6. **개인화 데이터의 개인정보 성격**: 관심·목표·역량의 보관 기간, 초기화 시 즉시 삭제 vs 보관 처리, 개인정보 처리방침 반영
7. **AI 나침반 결과와 `learning_goals`의 관계**: "사용자가 눌렀을 때만 목표로 설정" 확정 방향의 데이터 흐름
8. **역할(학습자 유형)별 시작 안내 콘텐츠의 관리 방식**: 코드에 고정 / 콘텐츠 파일
9. **CDN·캐시 도입 시 개인화 응답 처리**(`Cache-Control: private`, `Vary`)
10. **Phase 4 이후 CI(E2E 포함)의 실제 통과 여부**: 이 세션에서 GitHub 확인 권한 없음

---

## 12. 사용자 결정이 필요한 미확정 정책

1. 학습자 유형의 이름과 값: 입문자/개발자/탐색 중 확정 여부, 가입 시 필수/선택, 이후 변경 가능 여부
2. 학습자 유형 저장 위치: `user_settings` 컬럼(최소 변경) / 별도 `user_profiles`
3. 개인화 OFF 상태에서 관심 기술·목표를 **입력·보관**할 수 있는지 (사용만 안 함 vs 입력 자체 불가)
4. 개인화 OFF로 바꿀 때 기존 관심·목표 데이터 처리: 보관 / 삭제
5. "초기화"의 범위: 관심·목표·역량 전부 / 일부. 목표는 보관 처리(archived)로 확정할지
6. OFF 회원이 추천 API를 호출할 때: 빈 결과 / 403
7. Dev "기초 자료"의 정의와 관리 주체: 공식 문서 링크 목록 / Career 단원 / 둘 다
8. Career 게스트 퀴즈 체험 허용 여부, 게스트 활동 체크의 브라우저 임시 저장 허용 여부, 가입 시 이전 여부
9. AI 나침반 게스트 허용 여부 (기존 확정안은 로그인 필수), 허용 시 한도·비용 상한
10. 회원가입 횟수 제한 기준
11. 추천 근거로 쓸 태그 범위: 모든 규칙 태그 / 소스 태그·제목 일치만
12. 단원 난이도 표기 도입 여부와 단계
13. 추천 영역 노출 위치·개수
14. 구현 순서(10절 S1~S7) 확정

---

## 부록 A. 변경 대상 파일 제안 (수정하지 않음)

**백엔드 — 수정 후보**

| 파일 | 변경 내용 |
| :--- | :--- |
| `backend/app/models/user.py` | `UserSettings.learner_type` 추가 (또는 신규 모델) |
| `backend/app/schemas/auth.py` | `RegisterRequest.learner_type` 선택 필드 |
| `backend/app/schemas/user.py` | `UserSettingsOut`에 `learner_type` |
| `backend/app/services/auth.py` | `register_user`에서 유형 저장 |
| `backend/app/api/routes/auth.py` | 가입 횟수 제한 |
| `backend/app/api/routes/me.py` | `PATCH /api/me/settings` |
| `backend/app/api/deps.py` | 선택적 사용자 의존성 (필요 시) |
| `backend/app/models/learning.py` | 단원-기술 연결 모델, (선택) `level` |
| `backend/app/content_loader/schema.py`, `loader.py` | 단원 `technologies` 항목 |
| `backend/app/main.py` | 신규 라우터 등록 |

**백엔드 — 신규 후보**

- `backend/app/models/personalization.py` (관심·목표·역량)
- `backend/app/services/personalization.py`, `backend/app/services/recommendations.py`
- `backend/app/api/routes/me_personalization.py`, `me_recommendations.py`
- `backend/app/schemas/personalization.py`
- `backend/alembic/versions/0006_*.py` 이후 (작게 분할)
- (선택) `backend/content/technology_resources.yaml`

**프론트 — 수정·신규 후보**

| 파일 | 변경 내용 |
| :--- | :--- |
| `frontend/src/modals/SignupPopup.jsx`, `frontend/src/api/auth.js` | 유형 선택 |
| `frontend/src/auth/AuthProvider.jsx` | 설정 갱신 반영 |
| `frontend/src/components/common/HeaderNav.jsx` | 설정 진입 |
| `frontend/src/pages/home/HomePage.jsx`, `frontend/src/pages/dev/DevPage.jsx` | 추천 영역, 인증 상태 반영 |
| `frontend/src/pages/career/CareerHomePage.jsx`, `UnitPage.jsx`, `frontend/src/components/learn/QuizPanel.jsx` | 시작 안내, 게스트 체험 |
| 신규 `frontend/src/pages/settings/*`, `frontend/src/api/personalization.js`, `frontend/src/components/feed/RecommendedSection.jsx` | 설정 화면, 개인화 API, 추천 영역 |

**테스트 — 신규 후보**

- `backend/tests/integration/test_personalization.py`, `test_recommendations.py`
- `backend/tests/unit/test_personalization_boundary.py`
- `e2e/tests/personalization.spec.js`

## 부록 B. 이번 감사에서 확인한 사실

| 확인 | 내용 |
| :--- | :--- |
| API 인증 분류 | `get_current_user` 사용 라우트 6개(`me.py` 1, `me_learning.py` 5), 나머지 공개 [정적] |
| 격리 테스트 존재 | `test_learners_are_isolated`, `test_personal_endpoints_require_login`, `test_each_user_only_sees_their_own_profile` [정적] (최근 전체 실행 통과 [확인]) |
| 가입 시 설정 행 생성 | `register_user`에서 `UserSettings()` 생성 [정적], `test_register_creates_user_with_settings_and_logs_in` [정적] |
| v1 개인화·AI 코드 | `InterestPopup.jsx`, `AICompassModal.jsx`, `QuizModal.jsx`, `api/userAPI.js` 등이 옛 백엔드(`localhost:8000`) 직접 호출, 현재 라우트에서 미사용 [정적] |
| 작업 트리 | Phase 5 미커밋 변경 유지, 이번 작업으로 이 보고서 1개만 추가 |
