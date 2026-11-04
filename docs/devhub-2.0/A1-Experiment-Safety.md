# DevHub 2.0 — A1 단기 실험 안전 경계

A1은 짧은 로컬 RSS 실험을 위한 **차단 장치**다. 실험을 실행하는 기능이 아니다. 실험 허용 목록(`app/services/experiment_policy.py`의 `POLICIES`)은 비어 있으므로, 지금은 어떤 실험 소스도 로드·수집·진단·요약할 수 없다. 실제 소스를 허용 목록에 넣는 일은 B1에서 별도 승인 후 진행한다.

`terms: approved`와 정책 등록은 코드의 실행 설정일 뿐이다. 콘텐츠 이용 허락을 증명하지 않는다. 실제 이용 근거는 정책의 `basis_ref`가 가리키는 문서에 적는다.

## 1. 일반 설정과 실험 설정

| 구분 | 일반 소스 | 실험 소스 |
|---|---|---|
| 파일 | `content/sources.yaml` | `content/experiments/*.yaml` (예시: `sources.example.yaml`, 실행 불가) |
| 표시 | `scope` 없음, 일반 slug | `options.scope` + `exp-` slug. 둘 다 있거나 둘 다 없어야 함 |
| 허용 범위 | `status`, `options.terms`, `excerpt`, `ai_summary` | 위 조건에 더해 코드 정책 표와 모두 일치해야 함 |
| DB | `devhub_experiment`가 아닌 DB | 설정상 DB와 실제 연결 DB 모두 정확히 `devhub_experiment` |
| AI 요약 | 기존 조건 | **항상 거부** (A1) |

- 한 파일에 일반 소스와 실험 소스를 섞거나, 서로 다른 scope를 섞을 수 없다.
- 파일 이름·경로·복사본·심볼릭 링크는 판단에 쓰지 않는다. 내용(scope와 slug)과 코드 정책만 본다.
- scope는 DB의 `options`에 그대로 저장된다. 그래서 YAML 없이 DB에서 소스를 읽는 수집·요약 경로에서도 같은 검사가 다시 적용된다.

## 2. 코드 정책 표 (`experiment_policy.py`)

| 항목 | 내용 |
|---|---|
| `scope` | 정책 식별자 |
| `database` | `devhub_experiment`만 허용. YAML에서 바꿀 수 없음 |
| `starts_at` / `expires_at` | UTC, 시작 포함·종료 제외. 시간대가 없거나 순서가 틀리면 정책 전체 무효 |
| 소스별 `slug`, `adapter`, `kind`, `language`, `site_url`, `feed_url` | 하나라도 다르면 거부. URL은 scheme·host만 대소문자 무시. 경로·쿼리는 정확히 일치해야 하고 계정 정보가 있으면 거부 |
| `actions` | `metadata_read`, `metadata_store`, `excerpt_tagging`, `excerpt_store` 중 허용된 것. `ai_input`, `summary_store`, `public_export`는 A1에서 항상 거부 |
| `stored_fields` | `title`, `url`(필수)과 `published_at`, `author`, `external_id`, `source_tags`, `score`, `comment_count`, `view_count` 중 허용된 것. 나머지는 저장 전에 비움 |
| `basis_ref` | 이용 근거 문서 위치. 비어 있으면 정책 무효 |

YAML의 `excerpt`·`tagging_excerpt`는 정책 범위를 **좁힐 수만** 있다. 정책이 허용하지 않은 값을 켜면 요청 전에 거부된다.

## 3. 검사 위치

| 경로 | 검사 시점 | 거부 시 |
|---|---|---|
| `python -m app.content_loader sources` / `apply_sources()` | 쓰기 전(`--dry-run` 포함). 세션 자신의 연결에서 `SELECT DATABASE()`, autoflush 끔 | 추가·변경·retire 없음, 종료 코드 1 |
| `collect`, `collect --source`, `collect --group`(cron) | lock·`job_runs`·HTTP 전 | `refused`, 종료 코드 1 |
| `Collector.fetch` / `collect --dry-run` | robots.txt 요청 전 | 요청 없음 |
| `store_items()` | 쓰기 전, 세션 자신의 연결에서 다시 검사 | 소스 트랜잭션 롤백 |
| `diagnose` | 일반 소스는 DB 접속 없음. 실험 소스는 정책과 실제 DB 확인 후에만 요청 | `not requested`, 종료 코드 1 |
| `summarize` / `summarize_contents()` | 본문 파일을 읽거나 Gemini 클라이언트를 만들기 전 | 실험 DB에서는 아무것도 읽지·보내지·쓰지 않음 |

- 일반 소스는 `devhub_experiment`에서 수집·저장할 수 없다.
- 일반 소스 파일은 `devhub_experiment`에 로드할 수 없고, 실험 파일은 다른 DB에 로드할 수 없다.
- 실험 요청은 리다이렉트를 따라가지 않는다. robots.txt의 리다이렉트도 마찬가지다. 그래서 정책에는 리다이렉트된 뒤의 최종 주소를 적어야 한다.
- 일반 요청의 기존 robots·리다이렉트 처리는 그대로이고, 기존 훅을 지우지 않는다.
- 같은 링크에 대한 실험 요약은 일반 카드에 노출되지 않는다.

**방어 범위:** 파일을 잘못 고르거나, 복사·이름 변경을 하거나, scope를 빠뜨리거나, DB에 저장된 옵션을 다시 쓰는 실수는 막는다. 정책 코드 자체를 고치는 사람까지 막지는 않는다.

## 4. 소개문(excerpt) 처리

| 설정 | 일반 소스 | 실험 소스 |
|---|---|---|
| `tagging_excerpt` 미지정 | 태깅에 사용(기존 동작) | 사용 안 함 |
| `tagging_excerpt: false` | 사용 안 함 | 사용 안 함 |
| `tagging_excerpt: true` | 사용 | 정책에 `excerpt_tagging`이 있어야 함 |
| `excerpt: true` | 저장·표시(`terms: approved` 필요) | 정책에 `excerpt_store`가 있어야 함 |

RSS 응답 자체에는 소개문이 들어 있을 수 있다. 코드는 그 바이트를 받아 파싱한다. 위 설정이 막는 것은 소개문의 **태깅 사용·저장·외부 전송**이지, 수신 자체가 아니다.

## 5. 실험 준비 (B1, 별도 승인 후)

A1에서는 실험 DB·계정을 만들지 않았다. 아래 절차는 B1에서 승인을 받은 뒤 진행한다.

1. 기존 MariaDB에 `devhub_experiment` DB와 전용 계정을 만들고, 권한은 `devhub_experiment.*`로만 제한한다. 기존 DB·볼륨은 건드리지 않는다.
2. 환경값(예시, 비밀번호는 저장소에 넣지 않음):
   ```
   APP_ENV=local
   DATABASE_URL=mysql+pymysql://devhub_experiment:<password>@127.0.0.1:3307/devhub_experiment
   ```
3. 마이그레이션 → technologies → 실험 소스 파일 순서로 적재한다. 실험 소스 파일은 정책에 등록된 소스만 넣는다.
4. `python -m app.jobs diagnose --sources-file content/experiments/<file>.yaml`로 소스별 1회 확인한다.

**실험 절차에서 쓰지 않는 것:** `scripts/force_reset.py`, `scripts/seed_all.py`, `docker compose down -v`, 개발 DB 초기화.

## 6. 실행 전 체크리스트

- [ ] 정책의 `basis_ref` 문서에 소스별 이용 근거와 범위(메타데이터·소개문·저장 필드)가 적혀 있다
- [ ] 정책의 소스 identity(slug·URL·kind·language·adapter)가 실험 YAML과 같다. `feed_url`은 리다이렉트 없는 최종 주소다
- [ ] `starts_at`·`expires_at`이 정해져 있다(최대 30일)
- [ ] `actions`·`stored_fields`가 필요한 최소 범위다. AI 관련 행위는 없다
- [ ] 실제 연결 DB가 `devhub_experiment`이고, 일반 소스가 그 DB에 없다
- [ ] 예약 수집을 쓴다면 crontab이 `collect --group`을 호출하고, 그룹 목록에 실험 소스만 있다

## 7. 만료와 종료

- 만료는 **실행 거부**다. 만료 뒤에는 같은 cron 명령이 실행돼도 요청과 저장이 거부된다.
- 만료가 자동 삭제나 자동 연장을 뜻하지는 않는다. 기간을 바꾸려면 정책 코드를 직접 수정해야 한다.
- 종료 절차:
  1. crontab에서 실험 블록을 지운다.
  2. 정책이 만료됐거나 제거됐는지 확인한다.
  3. 마지막 실행 ID·시각과 아래 통계를 기록한다.
  4. 실험 데이터의 보존·삭제는 미리 정한 방침에 따라 `devhub_experiment`에만 적용한다.

## 8. 공개 범위

| 공개 가능 (기본) | 별도 확인 전 공개 금지 |
|---|---|
| 집계 통계(아래 템플릿), 아키텍처·테스트·재현 절차, 직접 만든 가상 카드 | 실제 글 제목·소개문·AI 요약, 실제 화면 캡처, 원문, DB 덤프, API 키 |

로컬 `diagnose`·`collect-report` 출력은 실제 제목을 포함할 수 있으므로 공개 README의 입력으로 자동 사용하지 않는다. 로컬에서 볼 수 있다는 것이 공개해도 된다는 뜻은 아니다. 데이터를 내보내는 도구는 만들지 않았다.

### 통계 템플릿

| 항목 | 값 |
|---|---|
| 기간 (UTC) | YYYY-MM-DD ~ YYYY-MM-DD |
| 소스 수 (News / Dev) | n / n |
| 예정 실행 / 실제 실행 / 정책상 거부 / 실패 | n / n / n / n |
| 초기 적재 / 기간 중 신규 | n / n |
| 날짜 누락 / 중복 링크 | n / n |
| 기술 태그가 붙은 글 비율 | n% (표본 n건) |

### 가상 카드 템플릿 (실제 콘텐츠 대신 사용)

```
[예시 출처] 예시 기술 블로그 · 2026-01-01
제목: 가상의 Kubernetes 운영 사례
기술: Kubernetes, Go
링크: https://example.invalid/post
```
