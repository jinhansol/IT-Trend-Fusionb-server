# DevHub 2.0 — P4 상세 설계: 관심 기술 · 역량 · 개인화 ON/OFF · 초기화

- 상태: **승인된 설계, 구현 완료(미커밋).** 8절은 승인안대로 적용했습니다.
- 구현 중 달라진 점:
  - 관심·역량 개수 초과, 중복, 잘못된 수준은 요청 자체가 잘못된 것이라 409 대신 422로 응답합니다(전체 교체 방식).
  - 없는 기술은 422 `UNKNOWN_TECHNOLOGY`, 새로 고른 retired 기술은 422 `RETIRED_TECHNOLOGY`로 응답하고, 오류 상세에 해당 slug를 담습니다.
  - 기술 선택 화면용 공개 API `GET /api/technologies`를 추가했습니다(읽기 전용, 누구에게나 같은 응답).
  - 응답에 `profile_status`(`off`/`empty`/`ready`)를 넣어 "켜짐 여부"와 "추천에 쓸 데이터가 있는지"를 구분합니다.
- 기준 코드: `f7cfbe5` (P3 반영, CI 통과). DB head 0008(개발 DB 적용 완료).
- 범위: A안 v0.2 단계표의 P4 — "관심·역량 + 개인화 모듈 경계 + 초기화".
- 근거 표기: [코드] 저장소에서 확인한 사실 · [정책] 이번 지시의 잠정 정책 · [제안] 승인이 필요한 이 문서의 제안

---

## 1. 범위와 정책

### 포함
1. 관심 기술 선택·관리
2. 사용자 역량(기술별 자기 평가) 데이터
3. 개인화 ON/OFF 설정
4. 개인화 데이터 초기화
5. 개인화 모듈의 읽기·쓰기 경계
6. 게스트·회원(OFF/ON) 상태별 동작 정의와 테스트
7. 기존 목표·진로 후보·학습 기록·XP 보존

### 제외
- 추천 API와 추천 영역(P5)
- AI 추천(P7)
- 관심·역량을 이용한 콘텐츠 정렬·필터 자동 적용
- 학습 기록 기반 역량 자동 산출(P5 이후 검토)

### 정책 → 설계 대응

| 정책 [정책] | 설계로 강제하는 방법 |
|---|---|
| 개인화는 기본 OFF, 사용자가 명시적으로 ON | `user_settings.personalization_enabled` 기본값 0은 기존 그대로입니다 [코드]. ON은 `PATCH /api/me/settings`의 명시적 요청으로만 바뀝니다. 가입·목표·후보·학습 API는 이 값을 쓰지 않습니다(P3 정책 테스트 확장). |
| OFF 전환 시 관심·역량 보관, 추천 미사용 | OFF는 스위치 값만 바꾸고 행을 지우지 않습니다. "추천에 쓸 수 있는가"는 개인화 모듈의 한 함수(`personalization.profile_for_recommendation`)만 판단하고, OFF면 빈 값을 돌려줍니다. P4에는 이 함수를 호출하는 곳이 없습니다(P5에서 사용). |
| 초기화는 관심·역량만 삭제 | `POST /api/me/personalization/reset`은 `user_interests`·`user_skills`의 본인 행만 지웁니다. 목표·후보·진행·XP·설정이 그대로인지 전후 비교 테스트로 확인합니다. |
| 목표·진로 후보·학습 진행·XP는 초기화 대상 아님 | 위 테스트와, 개인화 모듈이 그 모델들을 import하지 않는다는 AST 경계 테스트(P3 방식). |
| 학습자 유형은 추천 순위에 사용하지 않음 | 개인화 모듈은 `learner_type`을 읽지 않습니다(경계 테스트). P1 동일성 테스트를 ON 사용자까지 확장합니다. |
| AI 추천 구현 안 함 | LLM 의존성·API를 추가하지 않습니다. 레거시 `InterestPopup.jsx`·`AICompassModal.jsx`는 계속 미사용 상태로 둡니다 [코드]. |

---

## 2. 기존 코드 영향 분석

### 재사용 [코드]

| 대상 | 위치 | 쓰임 |
|---|---|---|
| 개인화 스위치 컬럼 | `models/user.py` `UserSettings.personalization_enabled` (기본 0) | ON/OFF 저장. 스키마 변경 없음 |
| 설정 API | `api/routes/me.py` `PATCH /api/me/settings`, `schemas/user.py` `SettingsUpdate`(extra=forbid, "not settable yet") | `personalization_enabled` 필드를 추가하고, "보낸 필드만 변경" 규칙은 유지 |
| 기술 분류 57개 | `Technology` | 관심·역량 대상 |
| 사용자 행 잠금·트랜잭션 | `services/transactions.py` (`lock_user`, `write_transaction`, `with_retry`) | 개수 상한·동시성 |
| 경계 테스트 방식 | `tests/unit/test_career_boundaries.py` (AST) | 개인화 모듈 경계 |
| 정책 테스트 방식 | `tests/integration/test_career_policy.py` (전후 스냅샷) | 초기화·ON/OFF 보존 |
| 동일성 테스트 | `test_learner_settings.py`, `test_careers_api.py` | 게스트 = 회원 OFF = 회원 ON(관심·역량 있음) |
| 설정 화면 | `frontend/src/pages/settings/SettingsPage.jsx` (학습자 유형 섹션) | 개인화·관심·역량·초기화 섹션 추가 |
| 기술 칩 UI | `components/feed/TechFilter.jsx` 스타일 | 관심 기술 선택 |

### 바꾸는 것 (최소)

| 파일 | 변경 |
|---|---|
| `schemas/user.py` | `SettingsUpdate.personalization_enabled: bool \| None` 추가(null 불가) |
| `api/routes/me.py` | 위 필드 반영. 다른 동작은 그대로 |
| `models/__init__.py`, `main.py` | 새 모델·라우터 등록 |
| `tests/conftest.py`, `test_migrations.py`, `test_app_startup.py`, `test_career_boundaries.py` | 새 테이블·모듈 |
| `SettingsPage.jsx` | 섹션 추가. 기존 학습자 유형 섹션은 그대로 |
| `README.md` | 문서 |

### 위험과 대응
1. **"설정 API가 스위치를 못 바꾼다"는 P1의 계약 변경**
   - `SettingsUpdate`가 `extra=forbid`라서 지금은 `personalization_enabled`를 보내면 422가 됩니다.
   - 이것을 검증하는 기존 테스트가 있습니다 [코드]: `tests/integration/test_learner_settings.py::test_invalid_settings_changes_are_rejected`의 `{"personalization_enabled": True}` 경우. P4에서는 이 경우를 "ON으로 바뀐다"는 테스트로 옮기고, `role` 같은 다른 거부 경우는 그대로 둡니다.
   - 이것은 의도된 변경이므로 보고서에 명시합니다.
2. **레거시 관심 팝업** [코드]
   - `modals/InterestPopup.jsx`는 옛 백엔드와 옛 사용자 id를 씁니다. 재사용하지 않고, 라우트·헤더에서 계속 숨깁니다.
3. **"OFF인데 관심 기술 편집"의 혼동**
   - OFF에서 편집을 허용하면 사용자가 "왜 반영이 안 되지?"라고 느낄 수 있습니다.
   - 화면에 "개인화가 꺼져 있어 추천에 쓰지 않습니다"를 상시 표시합니다. 허용 여부 자체는 결정 사항입니다(8절 #2).
4. **retired 기술**
   - 관심·역량 행은 보존하고, 응답에 `available:false`로 표시합니다. P5 추천에서는 제외합니다.
5. **ON 사용자의 공개 응답**
   - P4에는 사용처가 없으므로 공개 API 응답은 ON에서도 같아야 합니다. 동일성 테스트를 ON 사용자까지 확장해 강제합니다.

---

## 3. 데이터 설계 (마이그레이션 0009)

새 테이블 2개만 만듭니다. `user_settings`는 변경하지 않습니다(대안은 8절 #5). downgrade는 이 2개 테이블만 삭제합니다.

### `user_interests` (개인화 데이터)

| 컬럼 | 타입 | 비고 |
|---|---|---|
| user_id | FK → users CASCADE | PK 1 |
| technology_id | FK → technologies RESTRICT | PK 2, 인덱스 |
| created_at | DATETIME(6) | 선택 시각 |

- 사용자당 최대 20개 [제안].
- 순서·가중치는 두지 않습니다(관심 여부만).

### `user_skills` (개인화 데이터, 역량 수준은 4절에서 대안 비교)

| 컬럼 | 타입 | 비고 |
|---|---|---|
| user_id | FK → users CASCADE | PK 1 |
| technology_id | FK → technologies RESTRICT | PK 2, 인덱스 |
| level | VARCHAR(20) CHECK | 권장안 B: `learning` / `used` / `confident` |
| updated_at | DATETIME(6) | |

- 사용자당 최대 30개 [제안].
- 출처는 사용자 자기 평가뿐입니다. 학습 기록에서 자동으로 만들지 않습니다.

### 소유권

| 테이블 | 쓰는 곳 | 읽는 곳 |
|---|---|---|
| user_interests, user_skills | `services/personalization.py`만 | 같은 모듈만. P5 추천 모듈은 이 모듈의 공개 함수를 통해서만 읽음 |
| user_settings.personalization_enabled | `api/routes/me.py`(설정 API)만 | 개인화 모듈, `/api/me` |
| 목표·후보·진행·XP | 기존 서비스 | 개인화 모듈은 import 금지 |

---

## 4. 역량 데이터 수준과 입력 UX — 대안 비교

### 4.1 역량 수준

| 안 | 내용 | 장점 | 단점 | 평가 |
|---|---|---|---|---|
| A. 관심 기술만 | 역량을 따로 저장하지 않음 | 가장 단순. 입력 부담 최소 | P5에서 "이미 아는 것"과 "배우고 싶은 것"을 구분하지 못함 | 범위의 "사용자 역량 데이터"를 충족하지 못함 |
| **B. 3단계 자기 평가** | 기술별 `배우는 중` / `써 본 적 있음` / `자신 있음` | 고르기 쉽고 해석이 명확함. P5에서 "다음 단계" 판단에 충분함 | 주관적임(모든 자기 평가의 한계) | **권장** |
| C. 5단계 숫자 척도 | 1~5점 | 세분화됨 | 숫자의 정밀도가 실제보다 정확해 보이고, 사람마다 기준이 다름 | 비권장 |
| D. 학습 기록 자동 산출 | 완료 단원·퀴즈로 계산(저장 안 함) | 입력이 필요 없음 | 공개 단원이 1개뿐이라 의미가 없음. 학습 기록을 개인화에 쓰는 것이라 OFF 정책과 경계가 모호함 | P5 이후 "참고 표시"로만 검토 |

권장: **B를 저장하고, D는 P4에서 하지 않습니다.** 역량은 관심 기술과 독립입니다(관심 없이 역량만 있을 수 있음).

### 4.2 입력 UX

| 안 | 흐름 | 장점 | 단점 | 평가 |
|---|---|---|---|---|
| **1. 설정 화면 섹션** | 설정 → "개인화" 섹션: 스위치(설명 포함) → 관심 기술 칩 다중 선택(분야/언어/도구 그룹, 검색) → 역량 목록에서 기술 추가 후 3단계 선택 → 초기화 | 기존 화면 재사용. 강제하지 않음. 상태가 한곳에 모임 | 찾아가야 함 | **권장 (P4)** |
| 2. 가입 직후 마법사 | 가입 → 관심·역량 입력 단계 | 데이터 확보율이 높음 | "가입 ≠ 개인화 ON" 원칙과 충돌할 여지. 마찰 증가 | 비권장 |
| 3. 맥락 버튼 | Home/Dev 기술 필터·직무 화면에서 "관심 기술에 추가" | 자연스러움 | 쓰는 곳이 분산되어 경계 관리가 어려움 | P5 이후 검토 |

추가 UX 원칙 [제안]:
- ON 전환 시 "켜면 저장한 관심 기술·역량을 앞으로의 추천에 사용합니다. 언제든 끄거나 초기화할 수 있습니다." 문구와 함께 저장합니다(별도 동의 팝업 없음).
- OFF 상태에서는 각 섹션에 "개인화가 꺼져 있어 추천에 쓰지 않습니다"를 표시합니다.
- 초기화는 확인 대화상자에서 삭제 대상(관심·역량)과 유지 대상(목표·진로 후보·학습 기록·XP)을 명시합니다.

---

## 5. API 설계 (모두 로그인 필요, 본인 데이터만)

| 메서드·경로 | 동작 |
|---|---|
| `PATCH /api/me/settings` | 기존 API. `personalization_enabled: true\|false` 추가(null 불가). OFF는 데이터를 지우지 않음 |
| `GET /api/me/personalization` | `{enabled, interests: [{slug, name, kind, available}], skills: [{slug, name, level, available}], limits}`. OFF에서도 본인 데이터 조회 가능 |
| `PUT /api/me/personalization/interests` | body `{technologies: [slug...]}`. 전체 교체(멱등), 최대 20. 없는 기술은 422, retired는 404 |
| `PUT /api/me/personalization/skills` | body `{skills: [{technology, level}]}`. 전체 교체(멱등), 최대 30 |
| `POST /api/me/personalization/reset` | 본인의 관심·역량 행 삭제. 스위치 값 처리는 결정 사항(8절 #3). 204 |

- 전체 교체(PUT) 방식이라 개수 상한 검사가 요청 하나 안에서 끝납니다. 그래도 같은 사용자의 동시 PUT은 `lock_user`로 직렬화합니다.
- 공개 API(news, dev, trends, tracks, technologies, careers)는 변경하지 않습니다. 응답이 상태와 무관하다는 것을 테스트로 고정합니다.

---

## 6. 상태별 동작

| 기능 | 게스트 | 회원 · 개인화 OFF | 회원 · 개인화 ON |
|---|---|---|---|
| 공개 콘텐츠(Home·Dev·Career·직무) | 열람 | 열람 (게스트와 응답 동일) | 열람 (게스트와 응답 동일, P4 기준) |
| 학습·퀴즈·XP | 열람만 | 그대로 | 그대로 |
| 목표·진로 후보 | 로그인 안내 | 저장·관리 | 저장·관리 |
| 개인화 스위치 | 없음 | ON으로 변경 가능 | OFF로 변경 가능 |
| 관심·역량 편집 | 로그인 안내 | 결정 사항(8절 #2). 권장: 편집 가능 + "추천 미사용" 표시 | 편집 가능 |
| 관심·역량의 추천 사용 | – | 사용 안 함 (P5에서도) | P5부터 사용. P4에는 사용처 없음 |
| 초기화 | – | 가능 | 가능 |
| 학습자 유형 | – | 정적 안내만 | 정적 안내만 (추천 순위 미사용) |

---

## 7. 테스트 계획

| 영역 | 테스트 |
|---|---|
| 마이그레이션 0009 | upgrade/check/downgrade 0008/upgrade. 0008 데이터(목표·후보) 보존 |
| 설정 API | ON/OFF 전환, null·잘못된 타입 422, `learner_type`과 독립(서로 바꾸지 않음) |
| 관심·역량 API | 전체 교체·멱등, 상한(20/30) 409, 없는 기술 422, retired 404·기존 행 `available:false`, 401, 사용자 간 격리, 동시 PUT |
| OFF 보관 | ON에서 저장 → OFF → 행이 그대로, `profile_for_recommendation` 빈 값 → 다시 ON → 같은 값 |
| 초기화 | 관심·역량만 삭제. 목표·후보·활동·진행·퀴즈·XP·`learner_type` 전후 동일. 다른 사용자 데이터 무영향 |
| 상태별 동일성 | 공개 URL 목록(P1~P3 전체)의 응답이 게스트 = OFF = ON(관심·역량 있음) × 학습자 유형 4종에서 바이트 단위로 같음 |
| 경계 (AST) | `UserInterest`·`UserSkill`은 개인화 모듈만 import. 개인화 모듈은 목표·후보·진행·XP 모델과 `learner_type`을 쓰지 않음. 기존 서비스(content_feed, learning_*, career_*)는 개인화 모듈을 import하지 않음 |
| 정책 회귀 | P3 정책 테스트에 "스위치·초기화 전후 목표·후보 동일"을 추가 |
| 프론트엔드 | 스위치(문구·전환), 관심 칩 선택·저장, 역량 3단계 선택, OFF 표시, 초기화 확인·취소, 게스트 로그인 안내 |
| E2E | 가입 → 기본 OFF → 관심·역량 저장(OFF에서 "추천 미사용" 표시) → ON → OFF(데이터 유지) → 초기화(관심·역량만 사라지고 목표·XP 유지). 모바일 폭 |

---

## 8. 착수 전 결정 사항

| # | 결정 | 제안 |
|---|---|---|
| 1 | 역량 수준 | B: 3단계 자기 평가(`배우는 중`/`써 본 적 있음`/`자신 있음`). 학습 기록 자동 산출은 하지 않음 |
| 2 | OFF 상태에서 관심·역량 편집 허용 | 허용 + "추천 미사용" 표시. 대안: ON일 때만 편집 |
| 3 | 초기화가 스위치도 OFF로 바꾸는지 | 바꾸지 않음(데이터만 삭제). 대안: 초기화 = 삭제 + OFF |
| 4 | 개수 상한 | 관심 20, 역량 30 |
| 5 | ON/OFF·초기화 시각 기록 | 두지 않음(최소 변경). 대안: `user_settings`에 `personalization_changed_at` 추가(기존 테이블 변경) |
| 6 | 입력 UX | 설정 화면 섹션만. 맥락 버튼은 P5 이후 |
| 7 | 관심 기술 선택 범위 | 공개 기술 57개 전체를 분야·언어·프레임워크·도구 그룹으로 표시 |
| 8 | P1의 "스위치 변경 불가" 계약 변경 | 승인 필요(의도된 변경, 관련 테스트 갱신) |
| 9 | 개발 DB 0009 적용 | 구현 후 별도 승인(P2·P3와 같은 절차) |

---

## 9. 구현 순서 (우선순위)

1. **P4-1 데이터·경계**: 0009, 모델, 개인화 모듈 골격, AST 경계 테스트(먼저 실패하게 작성)
2. **P4-2 설정 스위치**: `PATCH /api/me/settings` 확장, ON/OFF 테스트, 상태별 동일성 테스트 확장
3. **P4-3 관심·역량 API**: GET/PUT, 상한·동시성·격리·retired
4. **P4-4 초기화**: reset API와 보존 정책 테스트(목표·후보·학습·XP·유형)
5. **P4-5 설정 화면**: 스위치, 관심 칩, 역량 3단계, 초기화 확인, 게스트 안내, Vitest
6. **P4-6 통합 검증**: E2E(상태 흐름·모바일), README, 전체 회귀, 개발 DB 0009 적용 요청

의존성:
- 1 → 2·3 → 4 → 5 → 6
- 2와 3은 병행할 수 있습니다.

예상 규모:
- 백엔드 신규 약 8개(마이그레이션, 모델, 서비스, 라우트, 스키마, 테스트 3), 기존 수정 6개
- 프론트엔드 설정 화면 섹션 3~4개
