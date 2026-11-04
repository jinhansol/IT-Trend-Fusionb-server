# DevHub 2.0 수동 실험 실행 안내 (News 공지 1건 + Atom 글 1건)

`python -m app.jobs trial MANIFEST [--dry-run]` (코드: `backend/app/jobs/trial.py`)

개인 PC에서 최대 48시간 동안 항목 2건을 확인하는 수동 명령이다. 일반 수집(`collect`), `content/sources.yaml`, `terms` 게이트와는 별개로 동작한다. 실험 출처는 `status: paused`, `terms: unverified`로 만들어지므로 `collect`가 수집하지 않는다.

## 실행 전 확인 (모두 충족해야 실행)

1. **이용 근거:** 각 항목의 저장·표시 근거(문서, 조항, 확인한 날짜)를 사람이 확인하고 매니페스트 `basis`에 적었다. robots 허용, 공개 RSS, 연결 성공은 이용 허락이 아니다.
2. **대상:** `target_url`이 저장할 원문 URL과 정확히 같다.
   - 공지(`notice_page`): 입력 URL과 같아야 한다.
   - Atom(`atom_entry`): 피드와 같은 호스트의 글 하나다.
3. **필드:** 허용 필드는 `title`, `url`, `published_at`, `source`이고, 근거가 있을 때만 `author`, `source_tags`를 추가한다. 소개문·본문·이미지는 어떤 경우에도 저장하지 않는다.
4. **기간:** `created_at`부터 `expires_at`까지 48시간 이하이고, 시간대를 포함한다. 만료된 뒤에는 실행이 거부된다.
5. **매니페스트 위치:** 저장소 밖에 둔다. 형식은 `backend/tests/fixtures/trial/manifest.example.yaml`(합성 예시)을 참고한다.
6. **DB:** `devhub_experiment` DB와 같은 이름의 전용 계정을 쓴다. 서버는 기존 로컬 docker compose MariaDB(`127.0.0.1:3307`)를 재사용해도 된다.
   - **루프백 접속만 사용한다.** `DATABASE_URL`의 호스트는 `127.0.0.1`이고, compose는 포트를 `127.0.0.1`에만 공개한다(`docker-compose.yml`의 `ports`). 다른 주소로 공개된 서버는 쓰지 않는다.
   - **계정 권한은 이 DB에만 부여한다.** 실행 전에 `SHOW GRANTS`로 확인한다(아래 "준비" 참고). `devhub_dev`, `devhub_test`, `*.*`에 대한 권한이 하나라도 보이면 실행하지 않는다.
   - 명령은 설정 URL, `SELECT DATABASE()`, `CURRENT_USER()`의 DB명과 계정명이 모두 `devhub_experiment`일 때만 진행한다. 이 검사는 사전 확인과 쓰기 트랜잭션 안에서 각각 수행된다. 포트는 검사하지 않으므로, 계정 권한이 다른 DB를 막는 유일한 경계다.

## 준비 (승인 후, 개인 PC)

DB 생성과 계정 생성은 별도 승인 후 관리자 계정으로 1회만 한다. 아래는 기존 로컬 compose 서버(3307)를 쓰는 예다.

```sql
-- 관리자(root)로 접속: docker compose exec mariadb mariadb -uroot -p
CREATE DATABASE devhub_experiment CHARACTER SET utf8mb4 COLLATE utf8mb4_uca1400_ai_ci;
-- 컨테이너 안의 서버는 호스트의 127.0.0.1 접속을 docker 게이트웨이 주소로 본다.
-- 그래서 dev/test 계정과 같이 '%'로 만들고, 외부 노출은 127.0.0.1 포트 공개로 막는다.
CREATE USER 'devhub_experiment'@'%' IDENTIFIED BY '<비밀번호>';
GRANT ALL PRIVILEGES ON devhub_experiment.* TO 'devhub_experiment'@'%';
```

전용 계정으로 접속해 권한과 접속 대상을 확인한다.

```sql
-- mariadb -h127.0.0.1 -P3307 -udevhub_experiment -p devhub_experiment
SHOW GRANTS;                              -- 아래 두 줄만 있어야 한다
-- GRANT USAGE ON *.* TO `devhub_experiment`@`%` IDENTIFIED BY PASSWORD '...'
-- GRANT ALL PRIVILEGES ON `devhub_experiment`.* TO `devhub_experiment`@`%`
SELECT DATABASE(), CURRENT_USER();        -- devhub_experiment, devhub_experiment@%
SHOW DATABASES;                           -- information_schema, devhub_experiment만 보여야 한다
```

```bash
cd backend
export DATABASE_URL='mysql+pymysql://devhub_experiment:<비밀번호>@127.0.0.1:3307/devhub_experiment'
uv run alembic upgrade head
uv run python -m app.content_loader technologies content/technologies.yaml
```

비밀번호와 `DATABASE_URL`은 출력하거나 커밋하지 않는다. Gemini 키는 필요 없다(`env -u GEMINI_API_KEY`로 실행해도 된다).

## 실행

```bash
uv run python -m app.jobs trial ~/devhub-trial/manifest.yaml --dry-run   # 먼저: DB 없이 읽기만
uv run python -m app.jobs trial ~/devhub-trial/manifest.yaml             # 결과 확인 후 저장
```

처리 순서는 다음과 같고, 각 단계가 실패하면 다음 단계로 가지 않는다.

1. 매니페스트와 기간 확인
   - URL은 https, 기본 포트(443), 공개 호스트여야 한다. 잘못된 포트, localhost, 사설·루프백 IP, 공백·제어 문자가 있으면 요청이나 DB 연결 없이 거부한다.
2. DB 확인(저장 시에만)
3. 항목별 robots.txt
   - 규칙을 읽지 못하면 거부한다. 404 등 오류 응답, robots.txt 대신 HTML 페이지, 연결 실패가 모두 해당한다.
   - 일반 수집기는 4xx 응답을 기존 정책대로 허용으로 본다. 이 정책은 바뀌지 않았다.
4. 페이지 또는 피드 1회 요청
   - 피드 대신 HTML 페이지가 오면 실패한다.
5. 저장 트랜잭션 안에서 쓰기 연결 재확인
6. 저장

만료는 시작할 때, 외부 요청마다 그 직전, 저장 트랜잭션에서 연결을 확인한 직후, 항목별 첫 쓰기 직전에 다시 검사한다. 실행 도중 만료되면 다음 요청을 보내지 않는다. 쓰기 중에 만료되면 트랜잭션 전체가 롤백된다.

요청 제한:
- 항목당 요청은 최대 2회(robots + 대상)다.
- 재시도하지 않는다.
- 리다이렉트는 따라가지 않는다.
- 매니페스트의 입력 호스트 외에는 요청하지 않는다.

같은 URL을 다시 저장하면 기존 행을 갱신하며, 새 행은 생기지 않는다.

종료 코드:
- `0`: 성공
- `1`: 요청 또는 파싱 실패. 아무것도 저장되지 않는다.
- `2`: 거부. 사유 코드: `trial_expired`, `invalid_manifest`, `robots_refused`, `not_the_experiment_database` 등

## 실행 중·후

- 공지 페이지 구조(`__NEXT_DATA__`, 공지 ID, 화면에 표시된 제목, 시간대가 포함된 `createdAt`)가 다르면 실패한다. 파서를 고치기 전에 사이트를 다시 검토한다.
- 화면에 출처를 표시할 조건(예: CC BY 4.0의 저자·제목·링크·라이선스)이 실제로 충족되는지 확인한다. 일반 카드가 라이선스 링크를 표시하는지는 아직 별도 확인이 필요하다.
- `expires_at`이 지나면 `devhub_experiment` DB와 계정을 정리한다. 별도 승인을 받고, 실험 DB에만 적용한다. dev/test DB는 건드리지 않는다.
