# DevHub 2.0 로컬 개발 가이드 (Windows)

개인 Windows PC에서 DevHub 2.0을 실행하고, 콘텐츠 수집을 안전하게 시험하는 방법입니다. 명령은 저장소의 `pyproject.toml`, `package.json`, `docker-compose.yml`, `.env.example`, CLI 구현(`app.content_loader`, `app.jobs`)을 기준으로 했습니다. 모든 명령은 **PowerShell** 기준입니다.

> **검증 상태**: 명령은 설정 파일과 CLI 코드로 확인했고, 같은 명령의 동작은 Linux 환경에서 확인했습니다. **Windows PC에서의 실행(winget·uv 설치, PowerShell 문법, Docker Desktop)은 아직 실측하지 않았습니다.** 실행 중 다른 결과가 나오면 이 문서를 고쳐 주세요.

순서: 1 설치 → 2 코드 받기 → 3 DB → 4 백엔드 → 5 콘텐츠 반영 → 6 수집 테스트 → 7 프론트엔드 → 8 테스트 → 9 종료

> 이 가이드의 수집 테스트는 **접속·파싱 확인(dry-run)** 이 기본입니다. 국내 소스의 재표시 이용 조건이 아직 확정되지 않았으므로, 외부 콘텐츠를 DB에 저장하는 수집은 이용 조건을 확인한 소스에만 하세요.

---

## 1. 필수 도구

| 도구 | 저장소가 요구하는 버전 | 설치 |
| :--- | :--- | :--- |
| Git | — | `winget install Git.Git` |
| uv | Python 3.12 (`backend/.python-version`, `requires-python >=3.12,<3.13`) | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| Node.js | 24 LTS (`.nvmrc`) | `winget install OpenJS.NodeJS.LTS` |
| Docker Desktop | MariaDB 11.4.13 (`docker-compose.yml`) | `winget install Docker.DockerDesktop` (WSL2, 설치 후 재부팅) |

- Python은 따로 설치하지 않아도 됩니다. `uv sync`가 `.python-version`에 맞는 Python을 받아옵니다.
- **정상**: 새 PowerShell 창에서 `git --version`, `uv --version`, `node -v`(v24.x), `docker version`이 모두 출력됩니다.
- winget의 `LTS` 패키지는 설치 시점의 최신 LTS를 받으므로 24가 아닐 수 있습니다. `node -v`가 v24.x가 아니면 [nodejs.org](https://nodejs.org)의 v24 설치 파일로 바꿔 설치하세요(저장소 기준: `.nvmrc` = 24).
- **오류**: "명령을 찾을 수 없음" → PowerShell을 새로 열어 PATH를 다시 읽습니다. Docker 명령이 실패하면 Docker Desktop 앱이 실행 중인지 확인합니다.
- 콘솔에서 한글이 깨지면 먼저 `$env:PYTHONUTF8 = "1"`을 입력합니다.

## 2. 코드 받기

```powershell
git clone https://github.com/jinhansol/IT-Trend-Fusionb-server.git
cd IT-Trend-Fusionb-server
git switch main
git pull
```

아직 병합되지 않은 PR을 시험할 때는 해당 브랜치로 바꿉니다(예: `git fetch origin feat/domestic-content` 후 `git switch feat/domestic-content`).

## 3. MariaDB

```powershell
# 저장소 루트
Copy-Item .env.example .env      # DEVHUB_DB_PORT=3307 과 로컬 전용 DB 비밀번호
docker compose up -d --wait mariadb
```

- **정상**: `Container devhub-mariadb-1 Healthy`. 볼륨이 처음 만들어질 때 `docker/mariadb/init/` 스크립트가 다음을 만듭니다.
  - `devhub_dev` DB + `devhub_dev` 계정 (개발용)
  - `devhub_test` DB + `devhub_test` 계정 (테스트용, 개발 DB에 접근 불가)
- PC의 Docker 볼륨은 다른 환경의 DB와 분리된 로컬 저장소입니다. 이미 다른 DevHub 볼륨이 있어 섞이지 않게 하려면 모든 `docker compose` 명령에 `-p devhub-local`을 붙입니다.
- **오류 확인**: `docker compose logs mariadb`
  - `port is already allocated` → 루트 `.env`의 `DEVHUB_DB_PORT`를 바꾸고, 아래 `backend/.env`의 `DATABASE_URL` 포트도 맞춥니다.
  - 비밀번호를 바꿨는데 접속이 안 됨 → 초기화 스크립트는 볼륨이 처음 만들어질 때만 실행됩니다. 기존 볼륨을 지우는 `down -v`는 로컬 데이터가 모두 사라지므로 주의합니다.

## 4. 백엔드

### 4-1. 환경변수

```powershell
cd backend
Copy-Item .env.example .env
```

| 변수 | 값 (`.env.example`) | 설명 |
| :--- | :--- | :--- |
| `APP_ENV` | `local` | `local`일 때 DB 이름이 `_test`로 끝나면 실행을 거부합니다 |
| `DATABASE_URL` | `mysql+pymysql://devhub_dev:...@127.0.0.1:3307/devhub_dev` | 개발 DB |
| `TEST_DATABASE_URL` | `...@127.0.0.1:3307/devhub_test` | 테스트 전용. 이름이 `_test`로 끝나야 함 |
| `JWT_SECRET` | 로컬 전용 예시 값 | 토큰 서명. 운영에서는 32바이트 이상 임의 값 필수 |
| `GEMINI_API_KEY` | (없음) | AI 요약 작업에만 필요. 로컬 실행·수집 테스트에는 넣지 않습니다 |

`backend/.env`는 Git에 포함되지 않습니다. 실제 비밀키를 커밋하지 마세요.

### 4-2. 설치·마이그레이션·실행

```powershell
uv sync                         # dev + jobs 의존성 그룹 설치 (uv.lock 기준)
uv run alembic upgrade head     # 정상: ... -> 0011 까지 적용
uv run uvicorn app.main:create_app --factory --reload
```

- **정상**: `Uvicorn running on http://127.0.0.1:8000`
- **확인**
  - `http://127.0.0.1:8000/api/health`: 프로세스 상태
  - `http://127.0.0.1:8000/api/health/ready`: DB 연결 상태
  - `http://127.0.0.1:8000/api/docs`: API 문서
- **오류**:
  - `Can't connect to MySQL server` → 3단계 컨테이너 상태 확인
  - `DATABASE_URL ...` / `APP_ENV=...` 로 시작하는 설정 오류 → `backend/.env` 값 확인

## 5. 콘텐츠 반영

서버를 띄운 창과 다른 PowerShell 창에서 `backend` 폴더 기준으로 실행합니다.

```powershell
uv run python -m app.content_loader technologies content/technologies.yaml   # 기술 분류 (먼저)
uv run python -m app.content_loader sources content/sources.yaml             # 수집 소스 등록
uv run python -m app.content_loader load content/python                      # 학습 트랙
```

- 모든 명령에 `--dry-run`을 붙이면 바뀔 내용만 보여 주고 되돌립니다.
- 같은 파일을 여러 번 반영해도 결과가 같습니다. 파일에서 지운 항목은 삭제되지 않고 `retired` 처리됩니다.
- 형식 오류가 하나라도 있으면 아무것도 반영하지 않습니다.

## 6. RSS 접속·파싱 테스트

수집은 웹 서버와 별개의 명령입니다. 웹 화면을 새로고침해도 외부 사이트에 요청하지 않습니다.

### dry-run과 저장 수집의 차이

| 명령 | 외부 요청 | DB 기록 |
| :--- | :--- | :--- |
| `collect --source <slug> --dry-run` | 피드 1회 | **없음** (`job_runs`도 기록하지 않음) |
| `collect --source <slug>` | 피드 1회 | 콘텐츠 저장 + `job_runs` 기록 |
| `collect --group news\|dev` | 허용 목록의 소스 | 저장 (`content/collect-schedule.yaml` 허용 목록만, 현재 비어 있음) |
| `collect` (옵션 없음) | 모든 활성 소스 | 저장. 이용 조건 확인 전에는 쓰지 마세요 |

### 접속·파싱만 확인하기

```powershell
uv run python -m app.jobs collect --source etnews --dry-run
```

소스는 하나씩 실행합니다. 실행 전에 브라우저로 그 사이트의 `/robots.txt`를 열어 피드 경로가 `Disallow`인지 확인하고, 금지된 소스는 실행하지 않습니다.

| 우선 확인 대상 (클라우드 개발 환경에서 네트워크 제한으로 검증하지 못한 소스) | 참고 |
| :--- | :--- |
| News: `etnews`, `ddaily`, `bloter`, `boannews` | |
| News: `ciokorea` | ITWorld Korea와 같은 운영사 계열이라 같은 robots.txt 제한이 있을 수 있음. 먼저 확인 |
| Dev: `toss-tech`, `naver-d2`, `daangn-tech`, `kakaopay-tech` | |

실행하지 않을 소스:
- `itworld-korea`: robots.txt가 `/feed/` 수집을 금지합니다.
- `woowahan-tech`: 사이트가 자동 접근을 403으로 차단합니다. `paused` 상태지만 `--source`로 이름을 직접 지정하면 실행되니 지정하지 마세요.

### 결과 읽는 법

| 출력 | 의미 | 조치 |
| :--- | :--- | :--- |
| `dry-run   fetched N ...` + 제목 3개 | 접속·파싱 성공 | 기록. **재표시 허락과는 별개** |
| `HTTP 404 from ...` | 피드 주소 변경 | 사이트 홈페이지의 RSS 링크를 찾아 기록 |
| `HTTP 403 from ...` | 사이트가 차단 | 수집 대상에서 제외. 우회하지 않음 |
| `ConnectError` / 시간 초과 | 네트워크 문제 | 한 번만 다시 시도 |
| `UnusableResponse` / 파싱 실패 | RSS 형식이 아님 | 기록 |

dry-run 출력에는 발행일이 나오지 않습니다. 최신성은 브라우저로 피드를 열어 최근 글 날짜를 확인합니다.

### 저장 수집과 중복 확인 (이용 조건을 확인한 소스만)

```powershell
uv run python -m app.jobs collect --source <slug>       # 저장
uv run python -m app.jobs collect --source <slug>       # 다시: 정상이면 new 0, updated 0
uv run python -m app.jobs collect-report --days 1       # 소스별 실행·성공·신규·마지막 성공 시각
```

## 7. 프론트엔드

```powershell
cd ..\frontend      # 새 PowerShell 창
npm ci
npm run dev
```

- **정상**: `Local: http://localhost:5173/`. 브라우저는 이 주소로 접속합니다. `/api` 요청은 Vite 프록시가 `127.0.0.1:8000`으로 전달합니다(`vite.config.js`, 바꾸려면 `VITE_DEV_API_PROXY_TARGET`).
- **화면 확인**: Home(`/`), News(`/news`), Dev(`/dev`), Career(`/career`). 수집한 콘텐츠가 없으면 "아직 수집된 …" 안내가 나오는 것이 정상입니다.
- **API 직접 확인** (PowerShell의 `curl`은 별칭이므로 `curl.exe` 사용):
  ```powershell
  curl.exe "http://127.0.0.1:8000/api/news?size=3"
  curl.exe "http://127.0.0.1:8000/api/dev/channels"
  curl.exe "http://127.0.0.1:8000/api/tracks"
  ```
- **오류**: 화면에 "불러오지 못했습니다" → 백엔드가 실행 중인지, 8000 포트인지 확인합니다.

## 8. 테스트

```powershell
cd backend
uv run pytest                          # 단위 + MariaDB 통합 (TEST_DATABASE_URL 필요)
uv run pytest -m "not integration"     # DB 없이 단위 테스트만
uv run ruff check; uv run ruff format --check

cd ..\frontend
npm test                               # Vitest
npm run build

cd ..\e2e                              # 브라우저 E2E (devhub_test 사용, 8100·5180 포트)
npm ci
npx playwright install chromium        # 처음 한 번
npx playwright test
```

- 통합 테스트는 연결된 DB 이름이 `_test`로 끝나는지 확인한 뒤에만 실행되고, 테스트가 끝날 때 테스트 DB의 앱 테이블을 비웁니다. 개발 DB에는 접근하지 않습니다.
- 백엔드 pytest와 E2E를 동시에 실행하지 마세요(같은 테스트 DB 사용).

## 9. 종료

```powershell
# 백엔드·프론트엔드 창: Ctrl + C
docker compose stop        # DB만 정지 (데이터 유지)
docker compose down        # 컨테이너 삭제 (데이터 볼륨 유지)
# docker compose down -v   # 로컬 DB 데이터까지 삭제. 처음부터 다시 할 때만
```

## 참고: 개발 DB 백업·복원

PowerShell의 `>` 리다이렉션은 파일 인코딩을 바꿀 수 있으므로, 덤프 파일은 컨테이너 안에서 만들고 `docker compose cp`로 복사합니다.

```powershell
# 백업 (저장소 루트, 개발 DB 전체)
docker compose exec -T mariadb sh -c 'mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction --routines --triggers devhub_dev > /tmp/devhub_dev-backup.sql'
docker compose cp mariadb:/tmp/devhub_dev-backup.sql .\devhub_dev-backup.sql

# 복원 (비어 있는 DB에만)
docker compose cp .\devhub_dev-backup.sql mariadb:/tmp/devhub_dev-restore.sql
docker compose exec -T mariadb sh -c 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" devhub_dev < /tmp/devhub_dev-restore.sql'
```

백업 파일에는 계정 이메일·비밀번호 해시·토큰 해시가 들어 있습니다. Git에 올리거나 공유하지 마세요.
