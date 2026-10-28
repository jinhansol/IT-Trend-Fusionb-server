# DevHub 2.0 — A안 v0.2 통합 설계 및 기존 코드 적합성 검증

| 항목 | 내용 |
| :--- | :--- |
| 작성일 | 2026-10-28 |
| 기준 코드 | `main` `927cc4a` + Phase 5 미커밋 변경(작업 트리) |
| 작업 성격 | 구현 전 설계 검증. 코드·테스트·DB·의존성 변경 없음, 마이그레이션·테스트 실행 없음, 커밋·push 없음 |

**근거 표기**

| 표기 | 뜻 |
| :--- | :--- |
| **[코드]** | 이번 작업에서 소스를 직접 읽어 확인 |
| **[이전 실행]** | 이 세션 앞선 작업에서 실행한 결과 (이번에는 재실행하지 않음) |
| **[추정]** | 실데이터·운영 환경에 대한 예상 |

**이번에 테스트를 재실행하지 않은 이유:** 백엔드 통합 테스트는 테스트 DB의 행을 지우고 Alembic upgrade/downgrade를 실행합니다(`tests/conftest.py` `clean_db`, `tests/integration/test_migrations.py`). 이는 "DB 데이터 변경 금지, 마이그레이션 실행 금지" 조건에 걸리므로 실행하지 않았습니다. 또한 이번 작업 시점에 Docker 데몬이 꺼져 있어 DB 상태를 직접 조회하지 않았습니다.

**판정 기호:** PASS / CONDITIONAL / BLOCKED / UNVERIFIED (요청서 정의 그대로)

---

## 1. Executive Summary

**최종 판정: CONDITIONAL GO**

A안 v0.2의 큰 방향은 현재 코드와 양립합니다.
- 공개 콘텐츠와 회원 기록의 분리
- 개인화 기본 OFF
- Career 기존 구현 보존
- Dev와 Career의 책임 분리
- 공통 기술 ID

기존 테이블·API를 바꾸지 않고 **덧붙이는 방식**으로 진행할 수 있으며, 전면 재작성이 필요한 지점은 발견되지 않았습니다.

다만 구현 전에 다음을 확정해야 합니다.

1. **역할 필드 분리 (구현 방식에 따라 BLOCKED)**
   - `users.role`은 이미 인증·인가용입니다: `user`/`admin` CHECK 제약, `/api/me` 응답의 `role`. [코드] `backend/app/models/user.py` `USER_ROLES`, `backend/app/schemas/user.py` `UserPublic.role`
   - A안의 입문자/개발자/탐색 중을 이 컬럼이나 같은 이름으로 구현하면 정책 위반이 됩니다. 별도 필드와 다른 이름이 전제 조건입니다.
2. **"목표" 개념의 이중 의미 정리**
   - v0.2는 일반 회원(OFF)도 학습 목표를 직접 저장할 수 있게 하면서, 개인화 초기화와 목표의 관계는 "검증 후 결정"으로 남겨 두었습니다.
   - 목표를 개인화 데이터로 둘지 Career 성장 데이터로 둘지 정하지 않으면, 초기화가 사용자가 직접 저장한 목표를 지우는 모순이 생깁니다(11절 C-1).
3. **역할별 "시작 안내"와 "추천"의 경계 정의**
   - 역할에 따라 특정 트랙을 첫 화면에 보여 주는 것이 "추천 순위 변경"인지 기준이 없습니다(11절 C-2).
4. **"사용자가 선택한 학습 트랙"의 실체**
   - v0.2의 보존 대상에 포함되어 있지만, 현재 코드에는 트랙 선택 개념이 없습니다. 단원 진행 기록만 있습니다. [코드]
5. **콘텐츠 현실과 기능 범위의 차이 (UNVERIFIED·데이터 부족)**
   - Career 학습 콘텐츠: 트랙 1개, 단원 1개 [코드] `backend/content/python/units/`
   - Dev의 공식 문서·개념·튜토리얼 데이터 모델 없음 [코드]
   - 직무(진로) 데이터 없음 [코드]
   - Home·Dev 실수집 데이터 미확보 [이전 실행] 개발 DB `contents` 0건
   - 기능 구조는 만들 수 있지만, 실제 사용자 경험은 콘텐츠 확보에 좌우됩니다.

결정 1~4가 확정되면 다음 단계(학습자 유형 필드, 설정 API, 단원-기술 연결)는 기존 기능 영향 없이 착수할 수 있습니다.

---

## 2. A안 v0.2 정책별 검증 결과

### 2-1. 핵심 원칙 (v0.2 2절)

| 원칙 | 판정 | 근거·이유 |
| :--- | :--- | :--- |
| 게스트도 실질적 서비스 이용 | **PASS** | 공개 API: `GET /api/news`, `/api/dev/channels`, `/api/dev/channels/{c}/posts`, `/api/trends`, `/api/feed-status`, `/api/tracks...`. 인증 의존성 없음 [코드] `app/api/routes/content.py`, `learning.py`. 게스트 열람 E2E 통과 [이전 실행] `e2e/tests/learning.spec.js`(비로그인 단계), `feeds.spec.js` |
| 회원가입 ≠ 개인화 활성화 | **PASS** | 가입 시 `UserSettings()` 생성, `personalization_enabled` 기본 False [코드] `app/services/auth.py` `register_user`, `app/models/user.py` `UserSettings` |
| 개인화 기본 OFF | **PASS** | 동일. 이 값을 읽는 기능이 아직 없어 OFF가 사실상 유지됨 [코드] |
| 개인화는 접근 권한이 아니라 추천 개선 | **PASS** (설계 유지 시) | 공개 목록 API는 사용자 정보를 받지 않음 [코드] `content_feed.list_news`. 추천을 별도 API로 분리하면 유지됨(12절) |
| Home·Dev·Career 독립 이용 | **PASS** | 세 영역의 API·화면이 서로 호출하지 않음 [코드] `pages/home`, `pages/dev`, `pages/career` |
| 공통 기술 분류·콘텐츠 연결 공유 | **CONDITIONAL** | 기술 분류는 콘텐츠에만 연결됨(`content_technologies`). 학습 단원·트랙에는 연결 없음 [코드] `app/models/learning.py` |
| 학습 기록은 개인화 설정과 독립 보존 | **PASS** (구조상) | 학습 기록 테이블은 `users`와 학습 정의만 참조하고 설정 테이블과 FK 관계 없음 [코드] `app/models/progress.py`, `app/models/quiz.py` |

### 2-2. 사용자 상태별 (v0.2 3절)

| 정책 | 판정 | 근거·이유 |
| :--- | :--- | :--- |
| 게스트 Home·Dev 탐색 | **PASS** | 위 공개 API |
| 게스트 Career 트랙·단원 열람 | **PASS** | `GET /api/tracks/{t}/units/{u}` 공개, `UnitPage.jsx`가 비로그인에도 활동 표시 [코드] |
| 게스트 진로 정보·진로 탐색 체험 | **CONDITIONAL** | 직무 데이터·화면 없음 [코드]. 정적 정보는 새 콘텐츠로 가능, AI 체험은 비용 정책 필요 |
| 게스트 퀴즈 체험 (검토 대상) | **CONDITIONAL** | 채점은 로그인 필수이고 응시를 기록함 [코드] `me_learning.py` `submit_quiz`, `learning_progress._submit_quiz`. `QuizPanel`은 `loggedIn && detail`일 때만 표시 [코드] `UnitPage.jsx`. 기록하지 않는 채점 API를 새로 만들어야 가능 |
| 게스트 기록·XP 저장 없음 | **PASS** | 기록 API 5개 모두 `get_current_user` [코드] `me_learning.py`. 401 테스트 존재 [코드] `test_personal_endpoints_require_login` |
| 회원 OFF: 가입 시 역할 선택 | **CONDITIONAL** (구현 방식에 따라 **BLOCKED**) | `RegisterRequest`에 필드 없음 [코드] `schemas/auth.py`. `users.role`은 권한용 → 별도 필드 필수 |
| 역할은 안내·메뉴·진입점에만 | **CONDITIONAL** | "진입점"과 "추천"의 경계 미정의(11절 C-2) |
| 학습 기록·진행률·XP·퀴즈·이어보기 | **PASS** | Phase 4 구현 [코드] `learning_progress.py`, E2E 통과 [이전 실행] |
| OFF 회원의 진로 탐색 결과·학습 목표 직접 저장 | **CONDITIONAL** | 저장소 없음 [코드]. 목표의 소속(개인화 vs Career)이 미정(11절 C-1) |
| 저장된 목표·기록을 자동 추천에 미활용 | **PASS** (현재) | 추천 기능 자체가 없음 [코드]. 향후 모듈 경계로 강제 필요(12절) |
| 이어보기 허용, 기록 기반 신규 콘텐츠 자동 선정은 개인화 | **PASS** | `learning_progress.summary`의 `continue_unit`은 사용자의 기존 `user_unit_progress` 행 중 미완료·최근 활동 단원만 고름. 새 단원을 선정하지 않음 [코드] |
| OFF에서도 사용자 명시 필터·검색·정렬 허용 | **PASS** (필터·정렬) / **CONDITIONAL** (검색) | 기술 필터(`tech`), 정렬(`sort=latest\|popular`) 구현 [코드] `routes/content.py`. 검색 기능은 없음 |
| 개인화 ON 명시적 활성화 | **CONDITIONAL** | 설정 변경 API 없음 [코드] `routes/me.py`(조회만) |
| 관심 기술·목표·역량 구분 관리 | **CONDITIONAL** | 테이블 없음. 기술 ID는 재사용 가능 [코드] `Technology` |
| Home 관심 기술 뉴스 추천 | **CONDITIONAL** | 기술 필터 쿼리 재사용 가능 [코드] `content_feed._with_technology`. 데이터 품질 UNVERIFIED |
| Dev: 관심 기술 자료와 목표 관련 자료를 구분 추천 | **CONDITIONAL** | 목표 → 기술 연결이 있어야 함. 목표가 직무 기반이면 직무 → 기술 데이터도 필요 |
| Career 목표·학습 상태 기반 다음 학습 제안 | **CONDITIONAL** | 목표 → 트랙/기술, 단원-기술 연결 필요. 단원 1개라 제안 대상이 사실상 없음 |
| 추천 이유 표시 | **CONDITIONAL** | 데이터 계약 미정. 태깅 오탐이 이유에 그대로 노출됨 [이전 실행] 사례 점검: "컨테이너선"이 Docker로 태깅 |
| 전체 공개 콘텐츠 탐색 유지 | **PASS** (설계 유지 시) | 기존 목록 API를 개인화와 분리하면 유지 |
| OFF·초기화 시 학습 기록 보존 | **PASS** (구조상) | 2-1 참조 |

### 2-3. 영역별·데이터 정책 (v0.2 4~8절)

| 정책 | 판정 | 근거·이유 |
| :--- | :--- | :--- |
| Home: 빈도 ≠ 성장세 | **CONDITIONAL** | 그래프 캡션은 "기술 이름이 언급된 기사 수"로 정확하지만, 섹션 제목이 "IT 트렌드", 그래프가 "일별 언급 추이"라 동향으로 읽힐 수 있음 [코드] `HomePage.jsx` 35·37행, `TrendCharts.jsx` `DailyTrend`. 트렌드 차트 정리 결정이 이미 보류 중 |
| Home: 원문 출처·발행일 | **PASS** | 카드에 소스명·상대시간·원문 링크 표시, 발행일 없으면 수집 시각 사용 [코드] `ContentCard.jsx`, `Content.sort_at` |
| Home: 관련 기술 개념·개발 자료 연결 | **CONDITIONAL** | 기술 태그만 있음. 개념·자료 데이터 없음 |
| Dev: 블로그·개발 사례 | **PASS** (코드) / **UNVERIFIED** (데이터) | Dev.to·HN·SO·GeekNews·기업 블로그 어댑터 [코드] `app/integrations/sources.py`. 실수집 미확인 |
| Dev: 공식 문서·개념 설명·튜토리얼 | **CONDITIONAL** | 데이터 모델·콘텐츠 없음 [코드] |
| Dev → Career 단원 이동 | **CONDITIONAL** | 단원-기술 연결 없음 |
| Dev 열람으로 Career 완료·XP 지급 금지 | **PASS** | XP 사유가 DB CHECK로 `unit_completed`만 허용 [코드] `app/models/progress.py` `XP_REASONS`, `reason_valid`. 단원 완료는 활동 확인 + 퀴즈 통과만 인정 [코드] `learning_progress._evaluate`. Dev 열람 기록 자체가 없음 |
| Career 진로 탐색 (직무 소개·비교·나침반·저장) | **CONDITIONAL** | 데이터·API·화면 전무 [코드]. v1 `AICompassModal.jsx`는 옛 백엔드용이며 라우트에서 제외됨 |
| 진로 탐색과 학습의 독립 시작 | **PASS** | 학습은 진로 데이터 없이 동작 중 [코드] |
| 기존 트랙·단원·활동·퀴즈·진행률·XP 유지 | **PASS** | 5절 |
| 진로 필수 정책 (강제 선택 금지, 자동 목표 변경 금지 등) | **PASS** (설계 단계) | 구현 전이라 위반 코드 없음. 데이터 분리 설계로 강제 가능(6절) |
| 적합도 백분율 금지 | **PASS** | 신규 코드에 해당 표현 없음. v1 `CareerDashboard`의 스탯·차트는 라우트 제외 [코드] `router/AppRouter.jsx` |
| 외부 자료 불필요 복제 금지 | **CONDITIONAL** | 콘텐츠는 소스별로 행을 둠(`UNIQUE(source_id, url_hash)`). 같은 링크가 HN과 Dev.to에 동시에 있으면 2행. 소스별 지표 보존을 위한 의도된 설계 [코드] `models/content.py` `Content`. 학습 활동 URL(`learning_activities.url`)과 향후 Dev 자료 목록 사이 중복 가능성도 있음 |
| 기술 수준 / 주제 수준 연결 구분 | **CONDITIONAL** | 기술 수준만 존재. 주제 계층 없음 [코드] |
| 학습 기록 보존 대상: 완료·퀴즈·XP·진행률 | **PASS** | 해당 테이블 존재·격리 [코드] |
| 학습 기록 보존 대상: "사용자가 선택한 학습 트랙" | **UNVERIFIED** → **CONDITIONAL** | 트랙 선택 엔터티 없음 [코드]. 진행 기록에서 유도할지, 새 데이터로 둘지 정의 필요 |

---

## 3. 현재 코드 구조 및 재사용 가능 기능

### 3-1. 실제 API (공개/인증) [코드]

| 구분 | 라우트 | 파일 |
| :--- | :--- | :--- |
| 공개 | `POST /api/auth/register`, `/login`, `/refresh`, `/logout` | `app/api/routes/auth.py` |
| 공개 | `GET /api/health`, `/api/health/ready` | `health.py` |
| 공개 | `GET /api/tracks`, `/{t}`, `/{t}/units/{u}`, `/{t}/units/{u}/quiz`(정답 없음) | `learning.py` |
| 공개 (Phase 5, 미커밋) | `GET /api/news`, `/api/dev/channels`, `/api/dev/channels/{c}/posts`, `/api/trends`, `/api/feed-status` | `content.py` |
| 인증 | `GET /api/me` | `me.py` |
| 인증 | `GET /api/me/summary`, `/tracks/{t}/progress`, `/tracks/{t}/units/{u}/progress`, `POST /activities/{id}/confirm`, `POST /quizzes/{id}/attempts` | `me_learning.py` |

인증 라우트는 모두 `get_current_user`로 사용자를 정하고, 경로·본문에서 사용자 ID를 받지 않습니다. [코드] `app/api/deps.py`

### 3-2. 재사용 가능 기능

| 기능 | 위치 | v0.2에서의 용도 |
| :--- | :--- | :--- |
| 인증·토큰 회전·사용자 격리 | `core/security.py`, `services/auth.py`, `deps.get_current_user` | 회원 식별, 개인 데이터 API |
| `UserSettings` 1:1 행 | `models/user.py` | 개인화 ON/OFF, (선택) 학습자 유형 저장 |
| 학습 카탈로그·로더 | `models/learning.py`, `content_loader/` | 트랙·단원 확장, 단원-기술 연결 항목 |
| 진행·퀴즈·XP | `services/learning_progress.py`, `services/rewards.py` | 변경 없이 유지, 추천은 읽기만 |
| 기술 분류 57개, 콘텐츠-기술 연결 | `models/content.py` `Technology`, `TechnologyAlias`, `ContentTechnology` | 공통 기술 ID |
| 기술 필터 쿼리 | `services/content_feed.py` `_with_technology` | 관심 기술 콘텐츠 조회 |
| 파일 + 멱등 로더 | `content_loader/taxonomy.py` | 직무 데이터, Dev 자료 목록도 같은 방식으로 관리 가능 |
| 프론트 인증 상태·개인 데이터 훅 | `auth/AuthProvider.jsx`, `hooks/useMyResource.js` | 상태별 화면, 로그인 전환 재조회 |
| 로그인 안내 | `components/learn/LoginPrompt.jsx` | 게스트 전환 지점 |

---

## 4. Home·Dev·Career 책임 분리 평가

| 항목 | 판정 | 평가 |
| :--- | :--- | :--- |
| Home = 정보 발견 | **PASS** | 뉴스 소스(`kind: news`)만 노출 [코드] `content_feed._visible_sources("news")` |
| Dev = 기술 탐구 | **CONDITIONAL** | 현재 Dev는 "외부 글 모음"만 있음. v0.2가 정의한 공식 문서·개념·튜토리얼 축이 없음 |
| Career = 진로 + 학습 + 성장 | **CONDITIONAL** | 학습·성장은 구현, 진로 탐색은 전무 |
| Dev와 Career 중복 기능 | **PASS** | 현재 중복 없음. Dev는 열람만, Career는 활동·평가·기록 [코드] |
| 경계 위험 | 주의 | 향후 Dev "튜토리얼·예제"가 Career "학습 활동"과 겹칠 수 있음. "Dev = 참고 자료(완료 개념 없음), Career = 평가 가능한 학습"으로 데이터 모델을 분리하면 충돌하지 않음 |
| 공통 콘텐츠 저장소 | **PASS** | Home·Dev가 같은 `contents` 테이블을 `kind`·`channel`로 나눠 사용 [코드] |

---

## 5. Career 기존 구현 보존 가능성

**판정: PASS**

| 보존 대상 | 근거 | v0.2 변경의 영향 |
| :--- | :--- | :--- |
| 트랙·단원·활동 (`learning_tracks/units/activities`) | [코드] `models/learning.py` | 새 연결 테이블(단원-기술)만 추가, 기존 컬럼 변경 없음 |
| 퀴즈·응시·답안 (`quizzes`, `quiz_*`) | [코드] `models/quiz.py` | 게스트 체험 채점을 추가해도 기록 테이블을 쓰지 않으면 영향 없음 |
| 진행·활동 기록 (`user_unit_progress`, `user_activity_records`) | [코드] `models/progress.py` | 개인화·진로 데이터와 FK 관계를 두지 않으면 영향 없음 |
| XP 원장 (`xp_ledger`, 사유 CHECK) | [코드] | Dev 열람 등 다른 사유를 추가하지 않는 한 영향 없음 |
| API (`/api/tracks...`, `/api/me/...`) | [코드] | 응답에 선택 필드만 추가하면 하위 호환 |
| 화면 (`CareerHomePage`, `TrackPage`, `UnitPage`, `QuizPanel`) | [코드] | 시작 안내·진로 영역을 별도 섹션으로 추가 |
| 테스트 | [코드] `tests/integration/test_learning_progress.py` 15개 시나리오, E2E `learning.spec.js` | 회귀 기준으로 그대로 사용 |

**주의**

- `CareerHomePage.jsx`의 "이어서 학습하기"가 비어 있을 때의 문구는 사용자가 직접 고르도록 안내합니다. 역할별 시작 안내를 여기에 넣을 경우 11절 C-2의 경계를 지켜야 합니다.
- `UnitPage`의 이전·다음 단원 링크는 카탈로그 순서이고 개인화가 아닙니다. [코드] `UnitDetail.prev/next`

---

## 6. 진로 탐색·학습 관리 통합 구조 검증

**판정: CONDITIONAL**. 구조는 타당하지만 데이터와 정책이 없습니다.

v0.2 5절의 필수 정책을 데이터 분리로 강제하는 최소 구조(제안)입니다.

| 데이터 | 성격 | 관계 |
| :--- | :--- | :--- |
| 직무(`career_roles` 등) | 공개 콘텐츠, 파일 관리 | 직무 ↔ 기술 **다대다**(`career_role_technologies`), 1:1 고정 금지 정책 충족 |
| 진로 후보 저장(`user_career_candidates`) | 사용자 기록, 진로 탐색 소유 | 사용자 ↔ 직무 다대다, "보류" 가능(저장 안 함) |
| 학습 목표(`learning_goals`) | 사용자 기록 (소속 결정 필요, 11절 C-1) | 직무·트랙·기술 중 선택 참조. **진로 후보와 별도 테이블** |
| 나침반 대화·결과 | 사용자 기록 (게스트 시 저장 안 함) | 결과는 후보 "제안"만, 자동 저장·목표 변경 없음 |

**정책 대응**

| v0.2 정책 | 구조적 보장 방법 |
| :--- | :--- |
| 자동 목표 변경 금지 | 진로 서비스가 `learning_goals`에 쓰지 않음. 목표 생성은 사용자 요청 API만 |
| 결과만으로 개인화 활성화 금지 | 진로 서비스가 `user_settings`를 수정하지 않음 |
| 적합도 백분율 금지 | 응답 스키마에 점수 필드를 두지 않음. 근거는 텍스트 목록으로 |

**실현 가능성**

- 직무 소개·비교는 직무 데이터(사람이 작성)만 있으면 AI 없이 구현할 수 있습니다.
- AI 나침반은 별도 개발이며 비용·남용 정책이 선행되어야 합니다. 현재 코드에 LLM 연동은 없습니다. [코드]
- 학습과의 연결: 직무 → 기술 → (단원-기술 연결) → 단원. 단원-기술 연결과 학습 콘텐츠 확충이 선행 조건입니다.

---

## 7. 게스트·일반 회원·개인화 회원 정책 충돌

| # | 충돌·위험 | 판정 | 근거 |
| ---: | :--- | :--- | :--- |
| 1 | `users.role`과 학습자 역할의 이름·의미 충돌 | **BLOCKED** (같은 필드 사용 시) / **PASS** (분리 시) | [코드] `USER_ROLES = ("user", "admin")`, CHECK `role_valid`, `UserPublic.role` |
| 2 | OFF 상태의 암묵적 추천 | **PASS** (현재) | 개인화 데이터 미존재 [코드]. 향후 위험 지점: `content_feed`·`learning_progress.summary`에 관심·목표 정렬을 직접 넣는 경우 |
| 3 | 공개 콘텐츠와 인증 기능의 충돌 | **PASS** | 경로 수준 분리 [코드] |
| 4 | 로그인 상태와 공개 API 응답 | **CONDITIONAL** | 프론트는 로그인 중 모든 요청에 토큰을 붙임 [코드] `api/client.js` 요청 인터셉터. 공개 API가 토큰에 따라 응답을 바꾸면 OFF 불변 검증이 복잡해짐 → 추천을 별도 인증 API로 분리 권장 |
| 5 | 학습 기록과 개인화 설정 결합 | **PASS** | FK 관계 없음 [코드] |
| 6 | 진로 결과와 학습 목표 결합 | **CONDITIONAL** | 6절 구조로 분리 필요 |
| 7 | 역할 기반 시작 안내 vs 추천 금지 | **CONDITIONAL** | 11절 C-2 |
| 8 | 회원가입 횟수 제한 없음 (게스트·회원 AI 한도 우회) | **CONDITIONAL** | [코드] `routes/auth.py` `register`는 제한기 미사용, `login`만 `login_limiter` 사용 |
| 9 | 실패 제한기가 프로세스 메모리 기반 | **CONDITIONAL** (AI 한도에 재사용 시) | [코드] `services/rate_limit.py` 모듈 주석에 한계 명시 |

---

## 8. 콘텐츠·기술 분류·학습 단원 연결 구조

| 항목 | 판정 | 근거·평가 |
| :--- | :--- | :--- |
| 기술 분류 구조 | **PASS** | 57개, kind 6종, 본문 별칭 199·태그 전용 40, 파일 관리·retire 정책 [코드] `content/technologies.yaml`, `taxonomy.py` |
| 콘텐츠 → 기술 | **PASS** (구조) / **UNVERIFIED** (품질) | 규칙 태깅 `services/tagging.py` `Tagger`. 단위 테스트 통과 [이전 실행]. 오탐·누락 사례 확인 [이전 실행]. 실데이터 정확도 미측정 |
| 단원 → 기술 | **CONDITIONAL** | 연결 없음 [코드]. 트랙 slug `python`과 기술 slug `python`은 이름만 같음 |
| 기술 수준 연결 (v0.2 7절 1단계) | **CONDITIONAL** | 단원-기술 연결 테이블과 단원 YAML 항목 추가로 가능 |
| 주제 수준 연결 (2단계) | **CONDITIONAL** (현재 불가) | 주제·난이도 개념 없음 [코드] `LearningUnit`. 사람이 검수한 연결 데이터가 필요 |
| "같은 태그 ≠ 학습 관련성" 원칙 | 정책 일치 | 기술 태그만으로 학습 추천을 만들면 이 원칙에 어긋남. 초기 Home·Dev → Career 링크는 "관련 기술 학습" 수준 표현으로 제한 권장 |

**권장 연결 단계**

1. 단원 YAML에 `technologies:`를 추가합니다(사람이 지정 = 검수된 근거).
2. 기술 페이지 수준으로 "이 기술의 뉴스·Dev 글·Career 단원"을 모읍니다.
3. 주제 수준 연결은 콘텐츠 확충 후 별도 결정합니다.

---

## 9. DB·API·프론트엔드 영향 분석

### 9-1. DB (모두 추가, 기존 변경 없음)

| 구분 | 후보 | 필수 여부 |
| :--- | :--- | :--- |
| 학습자 유형 | `user_settings.learner_type` NULL + CHECK, 또는 `user_profiles` | 필수 |
| 개인화 입력 | `user_interests`, `user_skill_assessments` | ON 기능에 필수 |
| 목표 | `learning_goals` (소속 결정 후) | v0.2상 OFF 회원에도 필요 |
| 진로 | `career_roles`, `career_role_technologies`, `user_career_candidates` | 진로 탐색에 필수 |
| 연결 | `learning_unit_technologies` | 연결 기능에 필수 |
| 선택 | `learning_units.level`, Dev 자료 목록(`technology_resources`), 태그 근거·신뢰도, 사용량 한도 테이블 | 선택 |

**마이그레이션 위험** [코드]
- MariaDB DDL은 트랜잭션 처리가 되지 않습니다. 기존 리비전처럼 작게 나누고, 다운그레이드는 테이블 삭제만 하는 규칙을 유지해야 합니다(`alembic/versions/0004`, `0005` 패턴).
- 기존 사용자의 새 컬럼은 NULL을 "미선택"으로 해석하므로 백필이 필요 없습니다.

### 9-2. API

| 변경 | 내용 | 하위 호환 |
| :--- | :--- | :--- |
| 수정 | `POST /api/auth/register`에 선택 필드 `learner_type` | 호환 (기존 요청 유효) |
| 수정 | `GET /api/me` 응답에 `settings.learner_type` 추가 | 호환 (필드 추가). `role` 의미 유지 |
| 신규 | `PATCH /api/me/settings`, 관심·목표·역량·진로 후보 CRUD, `POST /api/me/personalization/reset` | – |
| 신규 | `GET /api/me/recommendations?scope=` (ON 전용, 이유 포함, 개수 제한) | – |
| 신규 | 직무 공개 API, (선택) 게스트 퀴즈 체험 채점 | – |
| 유지 | 기존 공개 목록·학습·진행 API 전부 | – |

### 9-3. 프론트엔드

| 화면·파일 | 영향 |
| :--- | :--- |
| `modals/SignupPopup.jsx`, `api/auth.js` | 학습자 유형 선택 |
| 신규 설정 화면, `HeaderNav.jsx` | 개인화 ON/OFF·초기화, 관심·목표·역량 |
| `pages/home/HomePage.jsx`, `pages/dev/DevPage.jsx` | ON 전용 추천 영역(별도 섹션). 현재 이 화면들은 `useAuth`를 쓰지 않아 로그인 전환 시 재조회가 없음 [코드] → 추천 영역에만 `useMyResource` 패턴 적용 |
| `pages/career/*` | 진로 탐색 섹션, 시작 안내, (선택) 게스트 퀴즈 |
| 초기 로딩 | `AuthProvider`가 처음엔 `loading` [코드] → 개인 영역은 상태 확정 후 렌더 |

---

## 10. 보안·기록 보존·테스트 위험

| 위험 | 판정 | 근거·대응 |
| :--- | :--- | :--- |
| 사용자 간 데이터 접근 | **PASS** | 토큰 기반 사용자 결정, 격리 테스트 존재 [코드] `test_learners_are_isolated`, `test_each_user_only_sees_their_own_profile`. 신규 개인 API도 같은 규칙 적용 필요 |
| 계정 삭제 시 데이터 | **PASS** | 기록 테이블 `ON DELETE CASCADE`(users) [코드] `models/progress.py`, `models/quiz.py`. 신규 테이블도 동일 규칙 필요 |
| 학습 정의 삭제로 기록 손상 | **PASS** | 학습 정의 FK `RESTRICT`, 로더는 삭제 대신 retire [코드] |
| 개인화 초기화가 기록을 지움 | **PASS** (설계 유지 시) | 초기화 대상 테이블을 개인화 테이블로 한정. 목표 처리 방식은 결정 필요 |
| 가입 남용 | **CONDITIONAL** | 가입 횟수 제한 없음 [코드] |
| AI 비용 남용 | **CONDITIONAL** | 공유 저장소 기반 한도 없음 [코드] |
| 퀴즈 정답 노출 | **PASS** (수용된 결정) | 정답은 공개 저장소 파일에 있음(Phase 4 결정 D). 게스트 체험 채점을 열어도 추가 노출은 제한적. 대량 호출 제한은 필요 |
| 개인화 응답 캐시 | **CONDITIONAL** (배포 시) | 캐시 헤더 설정 없음 [코드]. CDN을 쓸 경우 개인 응답 공유 위험 |
| 테스트 기준선 | **UNVERIFIED** (이번 실행 안 함) | [이전 실행] 백엔드 203 passed, Vitest 29 passed, E2E 3 passed. CI의 Phase 4 이후 결과는 미확인 |

**필수 회귀 테스트 범위**
- `tests/integration/test_auth.py` (가입 필드)
- `test_learning_api.py`, `test_content_loader.py` (단원 YAML 확장)
- `test_learning_progress.py` (기록 보존)
- `test_content_api.py::test_read_endpoints_never_write` (공개 API 무쓰기)
- `test_collector.py`
- `tests/unit/test_app_startup.py` (import 부작용·모듈 경계)
- `e2e/tests/*.spec.js`

**신규 테스트 필수 항목**

| 영역 | 항목 |
| :--- | :--- |
| 개인화 OFF | 공개 목록 응답이 게스트와 동일 / 학습자 유형을 바꿔도 순서 동일 / 추천 API가 개인화 데이터를 읽지 않음 |
| 기록 보존 | 유형 변경·ON↔OFF·초기화·목표 삭제·진로 결과 삭제 전후 학습 기록·XP 동일 |
| 진로 | 진로 API가 `learning_goals`·`user_settings`를 수정하지 않음 |
| 권한 | 신규 개인 API의 401·사용자 격리 |
| 추천 | 모든 항목이 정해진 형식의 이유를 가짐 |

---

## 11. 설계상 모순 및 추가 결정 필요 사항

### 11-1. 모순 (구현 전 반드시 해소)

| ID | 모순 | 설명 | 선택지 |
| :--- | :--- | :--- | :--- |
| C-1 | **목표의 이중 소속** | 3.2는 OFF 회원도 목표를 "직접 저장"하고, 8절은 "직접 저장한 목표와 추천에 활용하는 목표를 구분할 필요"를 말하면서 "개인화 설정 초기화"와의 관계는 미정. 목표를 개인화 데이터로 두면 초기화가 사용자 저장 목표를 지움 | ⓐ 목표 = Career 성장 데이터(초기화 대상 아님). 개인화는 ON일 때 읽기만 함 ⓑ 목표 = 개인화 데이터 ⓒ 목표 테이블 하나 + "추천 활용 여부" 별도 설정 |
| C-2 | **역할별 진입점 vs 추천 금지** | "역할을 탐색 진입점에 활용"과 "역할로 추천 순위를 바꾸지 않음"의 경계가 없음. 예: 입문자에게 "Python 기초부터"를 첫 화면에 보이는 것이 허용되는지 | ⓐ 역할별로 고정된 정적 안내 문구·링크만 허용(같은 역할이면 모두 같고, 기록을 쓰지 않음) ⓑ 안내에서도 특정 콘텐츠 지목 금지 |
| C-3 | **"사용자가 선택한 학습 트랙" 보존** | 8절의 보존 대상이지만 트랙 선택 데이터가 없음 [코드] | ⓐ 진행 기록에서 유도(별도 데이터 없음) ⓑ 트랙 선택(주력 트랙) 데이터 신설. 설계 문서 후보 `user_track_selections` |
| C-4 | **복제 금지 vs 소스별 행** | 7절 "불필요한 복제 금지"와 Phase 5의 소스별 콘텐츠 행(같은 링크가 소스별로 저장) | ⓐ 소스별 지표 보존을 위한 예외로 명시 ⓑ URL 단위 하나로 통합하고 지표는 별도 테이블 (변경 범위 큼) |
| C-5 | **Home 트렌드 표현** | 4.1 "빈도를 성장세로 단정 금지"와 현재 "IT 트렌드"·"일별 언급 추이" 표현 | 차트 정리 결정과 함께 해소(축소·명칭 변경·급상승 전환) |

### 11-2. 추가 결정 필요

1. 학습자 유형 값·필수 여부·변경 가능 여부·저장 위치(`user_settings` 컬럼 / `user_profiles`)
2. 개인화 OFF로 바꿀 때 관심·역량 데이터 보관 또는 삭제
3. "초기화"의 범위(관심·역량·목표 활용 설정 중 무엇)
4. OFF 회원의 추천 API 응답(빈 결과 / 403)
5. 게스트 퀴즈 체험 허용 여부, 브라우저 임시 기록 허용 여부
6. 게스트 진로 탐색 체험 범위(정적 직무 정보만 / AI 포함), AI 사용 시 한도·비용 상한
7. 직무 데이터 출처와 관리 방식, 초기 직무 수
8. Dev "공식 문서·개념·튜토리얼"의 데이터 형태(링크 목록 / 자체 작성)
9. 추천 근거로 쓸 태그 범위(전체 규칙 태그 / 소스 태그·제목 일치만)
10. 검색 기능 도입 여부(v0.2 3.2에서 언급, 현재 없음)
11. 회원가입 횟수 제한 기준

---

## 12. 최소 변경 구현 전략

1. **기존 API·테이블은 고정합니다.** 공개 목록 API는 "수동 탐색" 전용으로 응답을 사용자와 무관하게 유지하고, 학습 진행 API는 변경하지 않습니다.
2. **추천은 별도 인증 API로 분리합니다.** `GET /api/me/recommendations`는 ON일 때만 결과를 주고, 개수를 제한하며, 이유를 포함합니다. offset 페이지네이션 충돌과 OFF 불변 검증 문제를 동시에 피합니다.
3. **개인화 데이터를 읽는 모듈은 하나로 둡니다**(예: `services/personalization.py`). 다른 서비스가 import하지 않도록 테스트로 강제합니다. 기존 `tests/unit/test_app_startup.py`의 import 검사 방식을 재사용합니다.
4. **진로·목표·개인화는 서로 쓰지 않습니다.** 각 서비스는 자기 테이블에만 씁니다(6절).
5. **연결 데이터는 파일 + 멱등 로더로 관리합니다.** 단원-기술, 직무-기술, Dev 자료 목록을 사람이 검수한 근거로 둡니다.
6. **LLM은 전제로 삼지 않습니다.** 진로 비교·추천 이유는 규칙과 데이터로 먼저 구현하고, AI 나침반은 별도 결정 후 추가합니다.

---

## 13. 단계별 개발 순서와 의존성

| 단계 | 내용 | 선행 조건 | 기존 기능 영향 |
| :--- | :--- | :--- | :--- |
| P0 | Phase 5 정리·커밋 (트렌드 표현 C-5 포함) | 사용자 결정 | 없음 |
| P1 | 학습자 유형 필드 + 가입 선택 입력 + 설정 API(유형·ON/OFF) + 가입 횟수 제한 | C-2 결정, 11-2 #1 | 가입·`/api/me` 응답 필드 추가(호환) |
| P2 | 단원-기술 연결(YAML·로더·응답 필드) + 기술 수준 연결 화면(Home·Dev → 관련 학습) | 없음 (P1과 병행 가능) | 학습 API 선택 필드 추가(호환) |
| P3 | 목표·진로 후보·직무 데이터 + 진로 탐색 화면(AI 없음) | C-1, 11-2 #7 | 없음 (신규) |
| P4 | 관심·역량 + 개인화 모듈 경계 + 초기화 | P1, C-1, 11-2 #2·#3 | 없음 (신규) |
| P5 | 추천 API + 이유 + 추천 영역 | P2, P4, 실수집 데이터 확보 | 없음 (신규 영역) |
| P6 | 게스트 퀴즈 체험 | 11-2 #5 | 학습 기록 미사용이면 없음 |
| P7 | AI 나침반 | AI 서비스·한도 결정, 가입 제한(P1) | 없음 (신규) |
| 병행 | Career 학습 콘텐츠 확충(Python 2~5단원 등) | 없음 | 없음 (파일 추가) |

---

## 14. 최종 판정 및 다음 단계 진행 조건

### 영역별 판정

| 영역 | 판정 |
| :--- | :--- |
| 공개 콘텐츠·게스트 탐색 | PASS |
| 개인화 기본 OFF·학습 기록 독립 | PASS |
| Career 기존 구현 보존 | PASS |
| Dev 열람과 Career 완료·XP 분리 | PASS |
| 역할(학습자 유형) 도입 | CONDITIONAL (`users.role` 사용 시 BLOCKED) |
| 목표·진로·개인화 데이터 관계 | CONDITIONAL (C-1) |
| 기술·단원 연결 | CONDITIONAL |
| Dev 공식 문서·개념 축, 진로 직무 데이터 | CONDITIONAL (데이터 없음) |
| 추천 품질·실데이터 | UNVERIFIED |
| 테스트 기준선(이번 실행) | UNVERIFIED (이전 실행 통과) |

### 최종: **CONDITIONAL GO**

**진행 조건 (P1·P2 착수 전)**

1. 학습자 유형은 `users.role`과 다른 필드·다른 이름으로 저장한다고 확정합니다(11-2 #1).
2. C-2(역할별 진입점 경계)를 확정합니다.
3. Phase 5 처리 방향(C-5 포함)을 확정하고 커밋합니다. 미커밋 상태로 다음 단계를 겹치지 않기 위해서입니다.

**P3·P4 착수 전 추가 조건**

4. C-1(목표 소속)과 C-3(트랙 선택)을 확정합니다.
5. 개인화 OFF·초기화 시 데이터 처리(11-2 #2·#3)를 확정합니다.
6. 직무 데이터 출처·범위(11-2 #7)를 확정합니다.

**P5 이후 조건**

7. 실수집 데이터 확보와 태깅 품질 표본 검수
8. AI 관련 정책(11-2 #6)

NO-GO에 해당하는 근본 모순은 발견되지 않았습니다. BLOCKED 항목은 "역할을 기존 권한 컬럼으로 구현하는 경우" 한 가지이며, 별도 필드로 설계하면 해소됩니다.

---

## 부록. 작업 전후 git 상태

**작업 전** (`git status --short`, HEAD `927cc4a`)

- 수정(M) 14개: Phase 5 미커밋 변경
  - `.github/workflows/ci.yml`, `README.md`, `e2e/global-setup.js`
  - `backend/app/content_loader/__main__.py`, `backend/app/content_loader/loader.py`, `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/models/__init__.py`
  - `backend/pyproject.toml`, `backend/uv.lock`, `backend/tests/conftest.py`, `backend/tests/integration/test_migrations.py`, `backend/tests/unit/test_app_startup.py`
  - `frontend/src/router/AppRouter.jsx`
- 미추적(??) 29개
  - Phase 5 신규 파일 27개(백엔드 모델·마이그레이션 0005·수집기·API·테스트·콘텐츠 파일, 프론트 Home·Dev·feed 컴포넌트, `e2e/tests/feeds.spec.js`, `backend/tests/e2e_seed.py` 등)
  - 이전 분석 보고서 2개: `DevHub-2.0-Phase5-Status-and-Integration-Report.md`, `DevHub-2.0-A-Policy-Technical-Impact-Report.md`
- 합계 43개 경로

**작업 후**

- 기존 43개 경로 변경 없음
- 이번 작업으로 미추적 파일 1개 추가: `DevHub-2.0-A-v0.2-Architecture-Validation.md`
- 합계 44개 경로
