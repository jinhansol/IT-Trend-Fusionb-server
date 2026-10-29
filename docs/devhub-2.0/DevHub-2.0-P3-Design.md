# DevHub 2.0 — P3 상세 설계: 직무 데이터 · 진로 후보 · 학습 목표 · 진로 탐색

- 상태: **승인된 설계 기록.** P3-1~P3-7로 구현했습니다. 8절 결정은 승인안대로 적용했고, 직무 콘텐츠는 UNVERIFIED 초안으로 `review/careers/`에 남아 있습니다.
- 기준 코드: `da9cfb3` (P2 반영, CI 통과). DB head 0007.
- 범위: A안 v0.2 단계표의 P3 — "목표·진로 후보·직무 데이터 + 진로 탐색 화면(AI 없음)".
- 근거 표기:
  - [코드]: 현재 저장소에서 확인한 사실
  - [결정]: 확정된 정책(C-1~C-5, 이번 지시)
  - [제안]: 이 문서의 제안. 승인 필요

---

## 1. 범위와 정책

### 포함
1. 직무 데이터(`career_roles`)와 직무 ↔ 기술 다대다 연결(`career_role_technologies`)
2. 사용자 진로 후보 저장(`user_career_candidates`)
3. 학습 목표 저장·관리(`learning_goals`)
4. Career 진로 탐색 화면: 직무 목록·상세, 후보 저장, 목표 추가
5. 진로 탐색과 기존 학습의 연결: 직무 → 기술 → 단원(P2 연결 재사용)

### 제외
- AI 진로 나침반(P7)
- 관심·역량 데이터와 개인화 모듈·초기화(P4)
- 추천 API(P5)
- 트랙 선택 기능(C-3 보류)

### 정책 → 설계 대응

| 정책 | 설계로 강제하는 방법 |
|---|---|
| 학습 목표는 Career 성장 데이터 [결정 C-1] | `learning_goals`는 학습 영역 테이블입니다. P4의 개인화 초기화 대상 목록에 넣지 않고, 테스트로 고정합니다. |
| 개인화 OFF에서도 목표를 직접 저장 [결정] | 목표·후보 API는 `personalization_enabled`를 읽지 않습니다. OFF 사용자로 CRUD 테스트를 합니다. |
| AI 나침반 제외 [결정] | LLM 의존성·API·화면을 추가하지 않습니다. 레거시 `AICompassModal.jsx`는 라우트에 연결하지 않은 상태로 둡니다 [코드]. |
| 진로 탐색 결과가 목표를 자동 변경하지 않음 [결정] | ① 진로 서비스(`career_*`)는 `learning_goals`에 쓰지 않습니다(import 경계 테스트 + 쓰기 전후 비교 테스트). ② 목표는 `POST/PATCH/DELETE /api/me/goals`로만 바뀝니다. ③ 화면의 "학습 목표로 추가"는 미리 채운 입력 양식을 열 뿐이고, 사용자가 저장을 눌러야 생성됩니다. |
| 진로 탐색 결과만으로 개인화 활성화 금지 [결정] | 진로·목표 서비스는 `user_settings`에 쓰지 않습니다. 모든 P3 쓰기 API 호출 전후로 `user_settings`가 같은지 테스트합니다. |
| 기존 학습 기록·XP 보존 [결정] | P3 테이블은 진행·XP 테이블과 FK 관계가 없습니다. 목표 달성은 XP를 주지 않습니다 [제안]. 모든 P3 API 호출 전후로 진행·XP 행이 같은지 테스트합니다. |
| 학습자 유형은 순위에 영향 없음 [결정 C-2] | 직무 목록은 파일의 `position` 순서로 고정합니다. 유형별 응답 동일성 테스트(P1 방식)에 새 공개 API를 추가합니다. |
| 게스트 공개 접근 [결정] | 직무 목록·상세는 공개입니다. 저장(후보·목표)만 로그인이 필요합니다. 게스트/회원 응답 동일성을 테스트합니다. |

---

## 2. 기존 코드 영향 분석

### 2.1 재사용하는 것 [코드]

| 대상 | 위치 | 쓰임 |
|---|---|---|
| 기술 분류 57개 | `models/content.py` `Technology`, `content/technologies.yaml` | 직무 ↔ 기술 연결 대상 |
| 단원 ↔ 기술 연결 (P2) | `learning_unit_technologies`, `services/learning_catalog.get_technology_units` | 직무 → 기술 → 단원 연결 |
| 파일 + 멱등 로더 | `content_loader/taxonomy.py` (검증 후 upsert, 파일에서 빠지면 retired) | 직무 파일 로더를 같은 방식으로 추가 |
| 인증 의존성 | `api/deps.get_current_user`, `/api/me/*` 라우터 패턴(`me.py`, `me_learning.py`) | 후보·목표 API |
| 공통 오류 | `core/errors.AppError` (예: `TechnologyNotFound`) | `CareerRoleNotFound`, `GoalNotFound` 등 |
| 쓰기 트랜잭션·재시도 | `services/learning_progress._write_transaction`, `_with_retry` | 목표·후보 쓰기(동시 요청의 개수 제한) |
| 테스트 기반 | `tests/conftest.py` 삭제 순서, `test_learner_settings`의 동일성 검사, `test_app_startup`의 import 검사 | 새 테이블·API 추가 |
| 화면 | `useApiResource`, `useMyResource`, `LoadState`, `LoginPrompt`, `TechFilter` 칩 스타일, `RelatedLearning` | 진로 화면 |

### 2.2 바꾸는 것 (최소)

| 파일 | 변경 | 영향 |
|---|---|---|
| `app/main.py` | 라우터 2개 등록(`careers`, `me_goals`) | 추가만 |
| `app/models/__init__.py` | 새 모델 export | 추가만 |
| `content_loader/__main__.py` | `careers` 하위 명령 | 기존 명령은 그대로 |
| `content_loader/schema.py` | 예약 트랙 slug 검사(2.3) | 현재 트랙 `python`은 영향 없음 |
| `tests/conftest.py` | `TABLES_IN_DELETE_ORDER`에 새 테이블 | 테스트 전용 |
| `tests/integration/test_migrations.py` | `HEAD_TABLES` | 테스트 전용 |
| `tests/integration/test_learner_settings.py` | 동일성 검사 URL 목록 | 테스트 전용 |
| `.github/workflows/ci.yml`, `e2e/global-setup.js` | 로드 순서에 `careers` 추가 | technologies → sources → **careers** → tracks |
| `frontend/src/router/AppRouter.jsx` | 라우트 3개 추가 | 기존 라우트는 그대로 |
| `frontend/src/pages/career/CareerHomePage.jsx` | "진로 탐색" 진입 카드, (로그인 시) "내 학습 목표" 섹션 | 기존 섹션·순서는 그대로 |
| `frontend/src/learner/learnerTypes.js` | (선택) `exploring` 안내에 "진로 탐색" 정적 링크 | C-2 범위(정적 링크) 안 |
| `README.md` | 로드 순서, 새 API | 문서 |

변경하지 않는 것:
- 학습 진행·퀴즈·XP 서비스와 API
- Home·Dev 콘텐츠 API
- 인증
- `user_settings` 스키마
- 기존 테이블

### 2.3 발견한 위험과 대응

1. **라우트 충돌**
   - 현재 `/career/:trackSlug`와 `/career/:trackSlug/:unitSlug`가 있습니다 [코드].
   - `/career/explore`, `/career/goals`, `/career/roles/:roleSlug`를 추가하면, React Router 7의 순위 규칙상 정적 세그먼트가 우선이라 동작은 합니다.
   - 하지만 slug가 `explore`/`goals`/`roles`인 트랙이 생기면 그 트랙에 접근할 수 없습니다.
   - → 트랙 로더가 예약 slug(`explore`, `goals`, `roles`)를 거부하도록 합니다 [제안]. 현재 트랙(`python`)은 해당하지 않습니다.
2. **직무 ↔ 단원 연결이 사실상 비어 있음**
   - 공개 단원은 Python 1단원 하나뿐입니다 [코드].
   - 직무 상세의 "관련 학습"은 대부분 비어 보이게 됩니다.
   - → 빈 상태 문구를 설계에 포함하고, 2~5단원 확정 시점을 결정 사항으로 둡니다(8절).
3. **retired 직무를 참조하는 사용자 데이터**
   - 파일에서 직무가 빠지면 retired 처리됩니다. FK는 `RESTRICT`이므로 행이 삭제되지 않습니다.
   - 후보·목표는 그대로 보존하고, 화면에 "더 이상 제공되지 않는 직무"로 표시합니다.
   - 공개 API에서는 숨깁니다.
4. **계정 삭제 API 없음** [코드]
   - 사용자 행이 지워지는 경로는 현재 없습니다.
   - 새 사용자 테이블은 기존 진행 테이블과 같이 `users` FK `ON DELETE CASCADE`로 둡니다(일관성).
5. **레거시 진로 화면** [코드]
   - `pages/CareerDashboard.jsx`, `modals/AICompassModal.jsx`, `api/roadmapAPI.js`는 옛 백엔드용이고 라우트에서 빠져 있습니다.
   - 재사용하지 않고 수정하지도 않습니다(CI의 "Lint everything (report only)" 경고는 기존 그대로입니다).
6. **개수 제한의 동시성**
   - 활성 목표 상한(예: 5개)을 "센 뒤 삽입"으로 검사하면, 동시 요청 때 상한을 넘을 수 있습니다.
   - → 사용자 행 `SELECT … FOR UPDATE`로 직렬화합니다. `me.py`의 `with_for_update` 패턴과 같습니다.

---

## 3. 데이터 설계 (마이그레이션 0008)

하나의 마이그레이션으로 4개 테이블을 만듭니다.
- 기존 테이블은 변경하지 않습니다.
- downgrade는 이 4개 테이블만 삭제합니다(MariaDB DDL 비트랜잭션 특성상 기존과 같은 방식).
- 테스트 DB에서 먼저 검증한 뒤, 개발 DB 적용은 별도로 승인을 받습니다.

### 3.1 `career_roles` (공개, 파일 관리)

| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | BIGINT UNSIGNED PK | |
| slug | VARCHAR(64) UNIQUE | `backend-developer` |
| name | VARCHAR(100) | "백엔드 개발자" |
| summary | VARCHAR(300) | 목록 카드용 한두 문장 |
| description_md | TEXT | 하는 일, 일하는 방식. 마크다운. 굵게 표시 규칙 검사를 재사용 |
| tasks | JSON | 대표 업무 3~8개 (문자열 배열) |
| reference_links | JSON | 근거 자료 `[{title, url}]`, http(s)만 [제안: 1개 이상 필수]. (`references`는 MariaDB 예약어라 피함) |
| position | INT | 목록 순서. 사용자·유형과 무관하게 고정 |
| status | VARCHAR(20) CHECK (`published`,`retired`) | |
| created_at, updated_at | DATETIME(6) UTC | |

연봉·채용 수요 같은 수치는 넣지 않습니다. 검증할 출처가 없고, C-5처럼 오해를 부를 수 있습니다 [제안].

### 3.2 `career_role_technologies` (공개, 파일 관리)

| 컬럼 | 타입 | 비고 |
|---|---|---|
| role_id | FK → career_roles RESTRICT | PK 1 |
| technology_id | FK → technologies RESTRICT | PK 2, 인덱스 |
| importance | VARCHAR(20) CHECK (`core`,`related`) | "핵심 기술" / "함께 쓰는 기술" [제안] |
| position | INT | 직무 안 표시 순서 |

- 다대다입니다. 한 기술이 여러 직무에 속할 수 있습니다(1:1 고정 금지).
- 로더 검증:
  - 없거나 retired인 기술이면 파일 전체를 거부합니다(P2와 같은 규칙).
  - 직무마다 `core` 기술 1개 이상이 있어야 합니다.

### 3.3 `user_career_candidates` (사용자 기록, 진로 탐색 소유)

| 컬럼 | 타입 | 비고 |
|---|---|---|
| user_id | FK → users CASCADE | PK 1 |
| role_id | FK → career_roles RESTRICT | PK 2 |
| note | VARCHAR(200) NULL | 사용자 메모(선택) |
| created_at, updated_at | DATETIME(6) UTC | |

- 저장은 멱등입니다(이미 있으면 메모만 갱신).
- 사용자당 최대 10개 [제안].
- "보류"는 저장하지 않는 것으로 표현합니다. 별도 상태 값은 두지 않습니다.

### 3.4 `learning_goals` (사용자 기록, Career 성장 데이터)

| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | BIGINT UNSIGNED PK | |
| user_id | FK → users CASCADE | 인덱스 (user_id, status) |
| title | VARCHAR(100) | 사용자가 쓴 목표 문장. 필수 |
| role_id | FK → career_roles RESTRICT, NULL | 선택 참조 |
| technology_id | FK → technologies RESTRICT, NULL | 선택 참조 |
| track_id | FK → learning_tracks RESTRICT, NULL | 선택 참조 |
| status | VARCHAR(20) CHECK (`active`,`achieved`,`archived`) | |
| target_date | DATE NULL | 선택 |
| achieved_at | DATETIME(6) NULL | 사용자가 "달성"으로 바꾼 시각 |
| created_at, updated_at | DATETIME(6) UTC | |

- CHECK: 참조는 **0개 또는 1개**(`role_id`·`technology_id`·`track_id` 중 최대 하나) [제안].
  - 참조가 없으면 자유 목표입니다(예: "매일 30분 공부").
- 활성(`active`) 목표는 사용자당 최대 5개 [제안].
- 달성은 사용자가 직접 표시합니다. 학습 완료에서 자동으로 달성되지 않고, XP도 지급하지 않습니다 [제안].
  - 이유: 목표 변경은 사용자 요청으로만 일어나야 하고, XP 규칙(단원 완료 = 100 XP)을 바꾸지 않기 위해서입니다.
- 삭제는 실제 삭제입니다. 사용자 본인 데이터이고, 학습 기록과 연결이 없습니다. 기록을 남기고 싶으면 `archived`를 씁니다 [제안].

### 3.5 소유권 정리 (쓰기 권한)

| 테이블 | 쓰는 곳 | 쓰지 않는 곳 (테스트로 강제) |
|---|---|---|
| career_roles, career_role_technologies | 콘텐츠 로더(`careers` 명령)만 | 모든 웹 요청 |
| user_career_candidates | `services/career_candidates.py` | 목표 서비스, 학습 서비스 |
| learning_goals | `services/learning_goals.py` | 진로 서비스, 학습 서비스, (P4) 개인화 초기화 |
| user_settings | 기존 `me.py` 설정 API만 | 모든 P3 서비스 |
| 진행·XP 테이블 | 기존 `learning_progress`, `rewards`만 | 모든 P3 서비스 |

---

## 4. 직무 데이터 파일과 로더

`backend/content/careers.yaml` (초안 예시):

```yaml
roles:
  - slug: backend-developer
    name: 백엔드 개발자
    position: 1
    summary: 서비스의 서버, 데이터베이스, API를 만들고 운영합니다.
    description_md: |
      ...
    tasks: ["API 설계와 구현", "데이터베이스 모델링", "장애 대응과 성능 개선"]
    technologies:
      core: [python, java, sql]          # content/technologies.yaml의 slug
      related: [docker, kubernetes, aws]
    references:
      - { title: "...", url: "https://..." }
```

- 명령: `uv run python -m app.content_loader careers content/careers.yaml [--dry-run]`
- 검증 후 upsert합니다. 파일에서 빠진 직무는 retired 처리하고, 연결은 파일 내용으로 동기화합니다(P2와 같은 방식).
- 로드 순서: **technologies → sources → careers → tracks**. careers는 기술 참조만 있고 트랙과는 서로 독립입니다.
- 초기 직무 수와 작성 방식·출처는 결정 사항입니다(8절 #1). 예시 후보 6개:
  - 백엔드, 프론트엔드, 데이터 분석, 데이터 엔지니어, DevOps·클라우드, AI·ML 엔지니어
- 직무 설명은 사람이 작성하고 검토합니다. Python 단원처럼 저장소의 검토 폴더에서 초안 → 확정 순서로 진행합니다.

---

## 5. API 설계

### 5.1 공개 (로그인 불필요, 읽기 전용, 응답이 사용자와 무관)

| 메서드·경로 | 응답 | 비고 |
|---|---|---|
| `GET /api/careers/roles` | `{items: [{slug, name, summary, core_technologies: [{slug,name}], technology_count}]}` | position 순서, published만 |
| `GET /api/careers/roles/{slug}` | `{slug, name, summary, description_md, tasks, references: [{title, url}], technologies: [{slug, name, importance, units: [{track, slug, position, title}]}]}` | 기술별 공개 단원 포함(N+1 요청 방지). 없거나 retired면 404 `CAREER_ROLE_NOT_FOUND`, 잘못된 slug는 422 |

비교 기능은 별도 API를 두지 않습니다. 화면에서 상세 2~3개를 가져와 나란히 보여 줍니다 [제안]. P3에 포함할지는 8절 #6에서 결정합니다.

### 5.2 진로 후보 (로그인 필요, 본인 데이터만)

| 메서드·경로 | 동작 |
|---|---|
| `GET /api/me/career-candidates` | 내 후보 목록. retired 직무는 `available: false`로 포함 |
| `PUT /api/me/career-candidates/{role_slug}` | 저장(멱등), body `{note?}`. 공개 직무만 가능. 상한 초과 시 409 `CANDIDATE_LIMIT` |
| `DELETE /api/me/career-candidates/{role_slug}` | 삭제(없어도 204) |

### 5.3 학습 목표 (로그인 필요, 본인 데이터만, 개인화 설정과 무관)

| 메서드·경로 | 동작 |
|---|---|
| `GET /api/me/goals?status=active` | 내 목표. 참조 대상 이름·slug와 연결 정보 포함(5.4) |
| `POST /api/me/goals` | body `{title, role?, technology?, track?, target_date?}` (참조는 slug). 활성 상한 초과 시 409 `GOAL_LIMIT` |
| `PATCH /api/me/goals/{id}` | title, target_date, status 변경. `achieved`로 바꾸면 `achieved_at` 기록 |
| `DELETE /api/me/goals/{id}` | 삭제. 남의 목표나 없는 id는 404(존재 여부를 노출하지 않음) |

### 5.4 학습과의 연결 (목표 응답에 포함)

참조 종류별 동작:
- **직무 참조**: 직무의 `core` 기술 → 그 기술을 다루는 공개 단원 목록
- **기술 참조**: 그 기술의 공개 단원 목록(P2 API와 같은 결과)
- **트랙 참조**: 그 트랙의 공개 단원 목록

각 단원에는 **본인의 진행 상태**(not_started / in_progress / completed)를 함께 줍니다. 기존 진행 기록을 읽기만 하고 쓰지 않습니다.

이것은 추천이 아닙니다. 사용자가 고른 대상에 대한 고정 목록이고, 순서는 카탈로그 순서입니다. 개인화 OFF에서도 보여 줄지는 8절 #5에서 결정합니다(제안: 보여 줌).

---

## 6. 화면 설계

| 경로 | 화면 | 게스트 | 로그인 |
|---|---|---|---|
| `/career` (기존) | + "진로 탐색" 진입 카드 | 보임 | 보임 |
| | + "내 학습 목표" 섹션(활성 목표 최대 5개, 진행 요약, 관리 링크) | 숨김 | 보임 (개인화 OFF 포함) |
| `/career/explore` | 직무 카드 목록(이름, 요약, 핵심 기술 칩) | 보임 | 보임 + 저장한 후보 표시 |
| `/career/roles/:roleSlug` | 직무 상세 (아래 목록) | 보임, 저장 버튼은 `LoginPrompt` | 저장·목표 추가 가능 |
| `/career/goals` | 목표 관리(추가·수정·달성·보관·삭제), 저장한 진로 후보 목록 | 로그인 안내 | 보임 |

직무 상세의 구성:
- 설명, 대표 업무
- 핵심·관련 기술 칩. 각 칩은 Career 단원, `/?tech=`, `/dev?tech=` 링크(P2 재사용)
- 근거 자료 링크
- "진로 후보에 저장" 버튼
- "학습 목표로 추가" 버튼: 양식을 열고, 제목은 "○○ 되기"로 미리 채웁니다. 저장은 사용자가 누릅니다.

화면 원칙:
- 문구는 "추천"이 아니라 "탐색"과 "내가 저장한"을 씁니다.
- 직무 목록 순서는 모든 사용자에게 같습니다.
- 진로 화면에서 학습 기록을 바꾸는 동작은 없습니다(단원 링크로 이동만 합니다).
- 모바일 390px에서 가로 넘침이 없어야 합니다(기존 기준).

---

## 7. 테스트 계획

| 영역 | 테스트 |
|---|---|
| 마이그레이션 | 0008 upgrade/check/downgrade 0007/upgrade. 기존 데이터 보존(0006 learner_type 테스트 방식). `HEAD_TABLES` 갱신 |
| 로더 | 정상 로드·멱등 재로드. 연결 동기화. 없거나 retired인 기술 거부(아무것도 쓰지 않음). `core` 없음 거부. 중복 slug. http(s)가 아닌 참고 링크. 굵게 표시 규칙. 파일에서 빠지면 retired. 예약 트랙 slug 거부 |
| 공개 API | 순서 고정. published만. 404/422. 기술별 단원(draft/retired 제외). **쓰기 없음**. 게스트/회원 동일. 학습자 유형별 동일 |
| 후보 API | 401(비로그인). 멱등 저장. 메모 갱신. 상한 409. retired 직무 저장 불가·기존 후보는 `available:false`로 보존. 삭제 멱등. 남의 데이터 접근 불가 |
| 목표 API | CRUD. 참조 0~1개 검증. 상한 409(동시 요청 포함). 상태 전이와 `achieved_at`. 남의 목표 404. **개인화 OFF 사용자도 저장 가능** |
| 정책 | ① 후보 저장·삭제 전후 `learning_goals`·`user_settings` 불변. ② 목표 CRUD 전후 진행·활동 기록·XP·`user_settings` 불변. ③ 직무 로더 재실행 전후 사용자 후보·목표 불변. ④ import 경계: `career_*` 모듈이 `LearningGoal`·`UserSettings`를 쓰지 않음(AST 검사). ⑤ 목표 달성으로 XP가 생기지 않음 |
| 회귀 | 백엔드 전체, Vitest, ESLint(CI 목록에 새 경로 추가), 빌드 |
| 프론트엔드 | 직무 목록·상세 렌더. 게스트 저장 버튼 → 로그인 안내. "목표로 추가"는 양식만 열고 저장 전에는 요청 없음. 목표 CRUD. retired 직무 표시 |
| E2E | 게스트 직무 탐색 → 로그인 → 후보 저장 → 목표 추가 → Career 홈 "내 학습 목표" → 단원 이동. 그 전후로 XP·진행 불변 |

---

## 8. 착수 전 결정 사항

| # | 결정 | 제안 |
|---|---|---|
| 1 | 직무 데이터 출처·작성 방식·초기 직무 수 (A안 11-2 #7) | 직접 작성 + 공개 자료 링크를 근거로 첨부(1개 이상 필수). 초기 6개. 연봉·수요 수치 제외. 검토 폴더에서 초안 검토 후 확정 |
| 2 | 직무 ↔ 기술 연결 수준 | `core`/`related` 2단계 |
| 3 | 목표 모델 | 제목 필수 + 참조 0~1개(직무·기술·트랙) + 상태 3종 + 목표일 선택. 활성 5개 상한 |
| 4 | 목표 달성 처리 | 사용자가 직접 표시. 자동 달성 없음. XP 없음 |
| 5 | 목표의 연결 학습·진행 표시를 개인화 OFF에서도 보일지 | 보임. 사용자가 고른 대상의 고정 목록이므로 추천이 아님 |
| 6 | 직무 비교 화면을 P3에 포함할지 | 포함하지 않음(P3 후속 또는 P5 전). 상세 화면만 먼저 |
| 7 | 진로 후보 상한·메모 | 10개, 메모 200자 |
| 8 | 목표 삭제 방식 | 실제 삭제 + 보관(`archived`) 상태 별도 제공 |
| 9 | 화면 경로와 예약 트랙 slug | `/career/explore`, `/career/roles/:slug`, `/career/goals`. 트랙 slug `explore`·`roles`·`goals` 금지 |
| 10 | Python 2~5단원 확정 시점 | P3 화면 검증 전에 확정 권장. 직무 → 단원 연결이 1단원 하나뿐이면 연결 효과를 확인하기 어려움 |
| 11 | 개발 DB 0008 적용 | 구현·테스트 DB 검증 후 별도 승인(이번과 같은 절차) |
| 12 | P3 설계 문서와 검토 자료의 커밋 여부 | 승인 시 docs 커밋(코드와 분리) |

---

## 9. 개발 순서 (우선순위)

각 단계는 테스트를 포함하고, 단계마다 검증한 뒤 다음 단계로 진행합니다. 커밋은 승인 후에 합니다.

1. **P3-1 데이터 기반**: 마이그레이션 0008(테스트 DB 검증), 모델, `careers` 로더와 스키마, 예약 slug 검사, CI·E2E 로드 순서
2. **P3-2 직무 콘텐츠**: `careers.yaml` 초안. 검토 폴더에서 사용자 검토를 받아야 확정합니다.
3. **P3-3 공개 API**: 직무 목록·상세(기술별 단원 포함), 쓰기 없음·동일성 테스트
4. **P3-4 진로 탐색 화면**: `/career/explore`, `/career/roles/:slug`, Career 홈 진입 카드
5. **P3-5 진로 후보**: API + 저장 버튼 + 정책 테스트
6. **P3-6 학습 목표**: API(상한 동시성 포함) + `/career/goals` + Career 홈 "내 학습 목표" + 목표의 연결 학습·진행 표시
7. **P3-7 통합 검증**: E2E, 정책 테스트 묶음, README, 화면 확인, 개발 DB 0008 적용 요청

의존성:
- 1 → 3 → 4
- 1 → 5 → 6
- 2는 1과 병행할 수 있고 3의 실데이터 화면 확인 전까지 필요합니다.
- 6의 연결 표시는 P2 연결과 10번 결정(2~5단원)의 영향을 받습니다.

예상 규모:
- 백엔드 신규 파일 약 10개(모델, 마이그레이션, 로더, 서비스 2, 라우트 2, 스키마, 테스트 4)
- 프론트엔드 신규 화면 3개 + 컴포넌트 3~4개
- 기존 파일 수정은 2.2의 목록으로 한정합니다.
