# DevHub 2.0 — P5-0 수집 구조·콘텐츠 검토

- 기준 코드: `ca8f702` (P4 완료). 개발 DB 0009. 작성: 2026-10-29.
- 범위: 분석·진단·설계. **코드·DB·콘텐츠는 변경하지 않았습니다.** (P5 설계서 보완만 문서로)
- 판정 표기
  - **CONFIRMED**: 코드·테스트·실행으로 확인
  - **UNVERIFIED**: 실행하지 못했거나 확인할 근거가 없음
  - **NOT IMPLEMENTED**: 코드에 해당 기능이 없음
- 실행한 외부 요청: 26회(소스당 1회, 재시도 없음). 모두 이 세션의 출구 프록시에서 거부되었습니다(6절). 진단 스크립트는 DB에 연결하지 않았고, 진단 전후 개발 DB의 `contents`·`job_runs`·`content_technologies`·`users`·`content_sources` 상태가 같음을 확인했습니다.

---

## 1. 현재 수집 아키텍처와 실제 호출 흐름

### 구성 요소
| 역할 | 파일·함수 | 판정 |
|---|---|---|
| 실행 진입점 (CLI, 웹 앱과 분리) | `backend/app/jobs/__main__.py` `main()` — `python -m app.jobs collect [--source SLUG] [--dry-run]` | CONFIRMED |
| 소스 목록 | DB `content_sources` ← `backend/content/sources.yaml`을 `content_loader sources`로 반영 (`app/content_loader/taxonomy.py` `read_sources`, `apply_sources`) | CONFIRMED |
| 실행 관리 | `app/jobs/runner.py` `Collector.sources()`, `run()`, `_run_locked()`, `dry_run()`, `fetch()` | CONFIRMED |
| HTTP | `app/integrations/http.py` `HttpFetcher.get()` → `_get_once()` (httpx) | CONFIRMED |
| 파싱(어댑터) | `app/integrations/sources.py` `collect_rss`·`parse_feed`, `collect_devto`, `collect_hackernews`, `collect_stackoverflow`, `adapters()` | CONFIRMED |
| 저장·중복 제거 | `app/jobs/store.py` `store_items()`, `normalize_url()`, `url_hash()`, `_tag()` | CONFIRMED |
| 기술 태깅 | `app/services/tagging.py` `load_tagger()`, `Tagger.match()` | CONFIRMED |
| 화면 제공(읽기) | `app/services/content_feed.py` `list_news()`(Home, 중복 묶음), `list_channel_posts()`(Dev), `feed_status()` | CONFIRMED |
| 정기 실행(스케줄러) | 저장소에 cron·스케줄러·워커 설정 없음. 수동 CLI만 있음 | **NOT IMPLEMENTED** |

### 호출 흐름 (실수집 `collect`)
```
app/jobs/__main__.py main()
  ├─ HttpFetcher(settings)                      # timeout 15s, UA, follow_redirects, 5MB 상한
  ├─ Collector(engine, fetcher, adapters(key))
  ├─ Collector.sources(slugs)                   # SELECT content_sources (active, position 순)
  └─ for source: Collector.run(source)
       ├─ SELECT GET_LOCK('devhub:collect:<id>', 0)   # 같은 소스 동시 실행 → skipped 기록
       └─ _run_locked(source)
            ├─ INSERT job_runs(status=running)        # 트랜잭션 1
            ├─ fetch() → adapters[source.adapter](fetcher, SourceConfig)   # 트랜잭션 밖에서 네트워크
            ├─ store_items(db, source, items, load_tagger(db))   # 트랜잭션 2 (소스 단위)
            │    ├─ normalize_url → url_hash → (source_id, url_hash) 기존 행 조회
            │    ├─ 신규: INSERT contents + _tag() → INSERT content_technologies(method=rule)
            │    └─ 기존: 값 갱신(지표 등), 제목·요약·태그가 바뀌면 재태깅
            └─ UPDATE job_runs(status, counts, error_summary)   # 트랜잭션 3, 실패해도 기록
```
- `--dry-run`은 `Collector.dry_run()`만 부릅니다. fetch와 파싱만 하고 **아무것도 쓰지 않습니다**(job_runs 포함). CONFIRMED: 코드와 `tests/integration/test_collector.py::test_dry_run_writes_nothing`.
  - 다만 소스 목록을 읽기 위해 DB에 연결(SELECT)은 합니다.

---

## 2. RSS · API · HTML 크롤링 사용 여부

26개 활성 소스(`content/sources.yaml`) 분류 (CONFIRMED: 파일과 어댑터 코드):

| 방식 | 소스 수 | 소스 | 근거 |
|---|---|---|---|
| RSS/Atom 피드 요청 + XML 파싱 (feedparser) | **23** | 뉴스 15(zdnet-korea, etnews, itworld-korea, ciokorea, koreaittimes, ddaily, bloter, boannews, techcrunch, wired-business, the-verge, ars-technica, venturebeat, infoq, slashdot), geeknews(feedburner), 국내 기업 기술블로그 7(toss, woowahan, kakao, naver-d2, daangn(medium), kakaopay, lycorp) | `adapter: rss` → `collect_rss` → `parse_feed` |
| 공식 REST API (JSON) | **3** | devto(Dev.to Forem API), hackernews(Algolia HN Search API), stackoverflow(Stack Exchange API 2.3) | `collect_devto`, `collect_hackernews`, `collect_stackoverflow` |
| HTML 페이지 요청·파싱 | **0** | – | HTML 파서 의존성 없음(`pyproject.toml`: feedparser, httpx만). `app/` 전체에 BeautifulSoup·lxml·trafilatura·selenium import 없음. **NOT IMPLEMENTED** |
| RSS/API로 링크 확보 후 원문 HTML 추가 요청(혼합) | **0** | – | 어댑터는 소스 URL(피드·API 엔드포인트)만 요청. `store_items`도 추가 요청 없음. **NOT IMPLEMENTED** |
| 기타 | 0 | – | – |

- `parse_feed`는 feedparser 결과 중 `title`, `link`, `id`, `summary`, `author`, `published/updated`, `tags`만 읽습니다. 피드가 본문(`content:encoded`, `entry.content`)을 함께 보내더라도 **읽지 않습니다**. CONFIRMED: `sources.py` 83–108행. 테스트 픽스처에도 content 요소가 없습니다.
- HTML 태그 제거는 파서가 아니라 정규식(`_TAG = re.compile(r"<[^>]+>")`)과 `html.unescape`로 합니다(`plain_text`, 47–55행). 요약을 한 줄 평문으로 만드는 용도입니다.

## 3. 뉴스 원문 HTML 추가 요청 여부

**하지 않습니다 — NOT IMPLEMENTED (CONFIRMED).** 뉴스 1건의 경로를 요청하신 10개 항목으로 추적하면 다음과 같습니다.

| # | 단계 | 실제 코드 | 판정 |
|---|---|---|---|
| 1 | 수집 대상 URL | DB `content_sources.feed_url` ← `sources.yaml` (`Collector.sources()` → `_config()` → `SourceConfig.feed_url`) | CONFIRMED |
| 2 | 최초 HTTP 요청 | `collect_rss()` → `HttpFetcher.get(feed_url)` → `_get_once()` (`httpx.Client.stream("GET")`) — 피드 URL 1회 | CONFIRMED |
| 3 | 응답 파싱 | `parse_feed()` → `feedparser.parse(bytes)`. 항목 0개이고 bozo/버전 없으면 `FetchError("not a readable RSS/Atom feed")` | CONFIRMED (픽스처 테스트 `test_collect_sources.py`) |
| 4 | 필드 추출 | 제목 `entry.title`→`plain_text`(500자). 요약 `entry.summary`→평문 300자(`EXCERPT_CHARS`). 발행일 `published_parsed` 또는 `updated_parsed`(UTC). 작성자 `entry.author`(200자). 출처는 피드가 아니라 `content_sources` 행. **본문은 추출하지 않음** | CONFIRMED |
| 5 | 원문 기사 URL 추가 요청 | 없음 | **NOT IMPLEMENTED** |
| 6 | HTML 본문 추출 파서 | 없음(정규식 태그 제거만) | **NOT IMPLEMENTED** |
| 7 | 기술 태그 생성 | 저장 시 `store_items()` → `_tag()` → `Tagger.match(title, excerpt, source_tags)`. 규칙(별칭 단어 일치)만 사용 | CONFIRMED (`test_tagging.py`) |
| 8 | URL 정규화·중복 제거 | `normalize_url()`(scheme·host 소문자, `utm_*`/`fbclid`/`gclid`/`ref_src` 제거, fragment 제거) → `url_hash()`(sha256). 같은 소스 안에서는 `UNIQUE(source_id, url_hash)`와 피드 내 중복 제거. 다른 소스 사이는 저장은 따로, Home 화면에서만 묶음(`content_feed._news_representatives`, P2) | CONFIRMED (`test_tagging.py::test_normalize_url...`, `test_news_dedupe.py`) |
| 9 | 저장 테이블 | `contents`(1행 = 소스 × 기사), `content_technologies`(rule 태그), `job_runs`(실행 기록) | CONFIRMED |
| 10 | 실패 기록 | 소스별 예외를 잡아 `job_runs.status=failed`, `error_summary`(최대 1000자, URL은 host+path만 — 쿼리스트링·API 키 제외, `http.py` `_where`), CLI 표준출력 한 줄. `logging` 모듈 사용 없음 | CONFIRMED (`test_collector.py::test_a_failing_source_is_recorded...`). 구조화 로그는 NOT IMPLEMENTED |

## 4. 소스별 수집 필드와 데이터 범위

어댑터 코드와 저장소 픽스처(`tests/fixtures/collect/`) 기준입니다. **실제 사이트 응답으로는 확인하지 못했습니다(UNVERIFIED, 6절).**

| 필드 | RSS (23) | Dev.to API | HN Algolia API | Stack Exchange API |
|---|---|---|---|---|
| 제목 | `title` | `title` | `title` | `title`(HTML 엔티티 해제) |
| 원문 URL | `link` (http/https만 허용) | `url` | `url`, 없으면 HN 토론 페이지 | `link` |
| 출처 | `content_sources` 행 | 같음 | 같음 | 같음 |
| 발행일 | `published` 또는 `updated` | `published_at` | `created_at_i` | `creation_date` |
| 작성자 | `author` | `user.name` | `author` | `owner.display_name` |
| 요약(excerpt) | **피드가 준 `summary`**를 평문 300자로 | **API `description`** 300자 | Ask/Show 글의 `story_text`만(링크 글은 없음) | **없음**(본문 미요청) |
| 기사 본문 | **없음** | **없음**(목록 API는 본문 미포함) | 없음 | 없음 |
| 기술 태그 입력 | 피드 `category` + 제목·요약 | `tag_list` + 제목·요약 | 제목·요약만 | `tags` + 제목 |
| 지표 | 없음(NULL) | 반응·댓글 | 포인트·댓글 | 점수·답변·조회 |
| 수집 시각 | `collected_at`(저장 시각), 발행일과 별도 컬럼. 정렬은 `sort_at = COALESCE(published_at, collected_at)` | 같음 | 같음 | 같음 |

- 출처 구분:
  - **RSS가 준 요약**: RSS `summary`, Dev.to `description`.
  - **HTML에서 추출한 실제 본문**: 없음.
  - **API가 준 콘텐츠**: 제목·태그·지표.
  - **수집 후 내부에서 생성한 요약**: `contents.summary` 컬럼과 `summary_status='pending'`은 저장 시 기록되지만, 이를 채우는 코드가 없습니다(`store.py` 97행 외 사용처 없음). **NOT IMPLEMENTED**
- **판단: 현재 수집 데이터는 "제목 + 출처가 제공한 짧은 요약(최대 300자) + 메타데이터" 수준이며, 기사 본문은 포함하지 않습니다.** 이는 `sources.yaml` 머리말("Full articles are never stored")과 `Content.excerpt` 주석의 의도와 일치합니다(CONFIRMED).

## 5. 26개 소스별 정상 접근 가능성

**전체 판정: 26개 모두 UNVERIFIED.** 이 세션의 출구 프록시가 모든 호스트로의 연결을 거부해, 원격 서버에 도달하지 못했습니다(6절).

- HTTP 응답 상태, 인증 필요 여부, 요청 제한 헤더, 응답 형식, 파싱 가능 여부, robots.txt·이용약관은 확인하지 못했습니다.
- 표의 "알려진 조건"은 코드나 이전 단계 기록에 근거한 것이고, 이번에 실측한 것이 아닙니다.

| # | slug | 방식 | 요청 URL (호스트) | 이번 결과 | 알려진 조건·검토 필요 사항 |
|---|---|---|---|---|---|
| 1 | zdnet-korea | RSS | www.zdnet.co.kr `/Include/news.xml` | 프록시 거부 (connect_rejected) | 국내 언론 RSS 재게시 범위 약관 검토 |
| 2 | etnews | RSS | rss.etnews.com `/Section903.xml` | 프록시 거부 | 〃 |
| 3 | itworld-korea | RSS | www.itworld.co.kr `/rss/all.xml` | 프록시 거부 | 〃 |
| 4 | ciokorea | RSS | www.ciokorea.com `/rss/all.xml` | 프록시 거부 | 〃 |
| 5 | koreaittimes | RSS | koreaittimes.com `/rss/allArticle.xml` | 프록시 거부 | site_url은 www, feed는 apex. 리다이렉트 가능성 |
| 6 | ddaily | RSS | www.ddaily.co.kr `/news/rss/allArticle.xml` | 프록시 거부 | 약관 검토 |
| 7 | bloter | RSS | www.bloter.net `/rss` | 프록시 거부 | 〃 |
| 8 | boannews | RSS | www.boannews.com `/media/rss.xml` | 프록시 거부 | 〃 |
| 9 | techcrunch | RSS | techcrunch.com `/feed/` | 프록시 거부 | 해외 언론 RSS 이용 조건 검토 |
| 10 | wired-business | RSS | www.wired.com `/feed/category/business/latest/rss` | 프록시 거부 | 〃 |
| 11 | the-verge | RSS | www.theverge.com `/rss/index.xml` | 프록시 거부 | 〃 |
| 12 | ars-technica | RSS | feeds.arstechnica.com `/arstechnica/index` | 프록시 거부 | 〃 |
| 13 | venturebeat | RSS | venturebeat.com `/feed/` | 프록시 거부 | 〃 |
| 14 | infoq | RSS | feeds.infoq.com `/` | 프록시 거부 | 〃 |
| 15 | slashdot | RSS | rss.slashdot.org `/Slashdot/slashdotMain` | 프록시 거부 | 〃 |
| 16 | devto | API | dev.to `/api/articles` (latest + `top=7`, 2회) | 프록시 거부(첫 요청) | 인증 불필요(공개 목록). API 이용 조건·요청 한도 검토 |
| 17 | hackernews | API | hn.algolia.com `/api/v1/search?tags=front_page` | 프록시 거부 | 인증 불필요. 요청 한도 검토 |
| 18 | stackoverflow | API | api.stackexchange.com `/2.3/questions?sort=hot` | 프록시 거부 | 키 없이 IP당 하루 300회, 키 사용 시 10,000회(Phase 5 계획 단계에서 공식 문서로 확인한 기록). 응답의 `backoff` 필드 준수 의무. 콘텐츠 CC BY-SA → 작성자·링크 표기 필요 |
| 19 | geeknews | RSS | feeds.feedburner.com `/geeknews-feed` | 프록시 거부 | FeedBurner 경유. 원 피드 주소 확인 필요 |
| 20 | toss-tech | RSS | toss.tech `/rss.xml` | 프록시 거부 | 기업 블로그 재게시 범위 검토 |
| 21 | woowahan-tech | RSS | techblog.woowahan.com `/feed/` | 프록시 거부 | 〃 |
| 22 | kakao-tech | RSS | tech.kakao.com `/feed/` | 프록시 거부 | 〃 |
| 23 | naver-d2 | RSS(Atom) | d2.naver.com `/d2.atom` | 프록시 거부 | 〃 |
| 24 | daangn-tech | RSS | medium.com `/feed/daangn` | 프록시 거부 | Medium RSS 이용 조건 |
| 25 | kakaopay-tech | RSS | tech.kakaopay.com `/rss` | 프록시 거부 | 〃 |
| 26 | lycorp-tech | RSS | techblog.lycorp.co.jp `/ko/feed/index.xml` | 프록시 거부 | 〃 |

- 진단 도구: `scratchpad/p5-0/probe_sources.py`
  - 실제 어댑터를 쓰고, 소스당 1회만 요청하며, 재시도는 하지 않습니다. DB에 연결하지 않습니다.
  - 원시 결과는 `scratchpad/p5-0/probe.json`에 있습니다.
- HTTP 200을 받더라도 수집·저장·재게시 권한이 있다는 뜻은 아닙니다. 소스별 이용약관과 robots.txt 검토는 별도로 필요합니다(UNVERIFIED, 12절).

## 6. ProxyError 원인 분석

| 가능성 | 판정 | 근거 |
|---|---|---|
| **실행 환경의 외부 접근 제한** | **CONFIRMED** | 26회 요청이 모두 `httpx.ProxyError: 403 Forbidden`으로 실패했습니다(CONNECT 단계, 각 0.27초 이내). 세션 프록시 상태(`$HTTPS_PROXY/__agentproxy/status`의 `recentRelayFailures`)에 해당 호스트들이 `kind: connect_rejected`로 기록되었습니다. 이 프록시는 세션 네트워크 정책으로 허용되지 않은 호스트를 거부하며, 안내 문서(`/root/.ccr/README.md`)는 "403/407은 대개 호스트가 이 세션에 허용되지 않은 것이며, 재시도하거나 우회하지 말 것"이라고 명시합니다. |
| 프록시 설정 오류 | 배제 | httpx가 `HTTPS_PROXY`(127.0.0.1)로 정상 연결해 프록시가 403을 응답했습니다. 같은 프록시를 거치는 허용 호스트(GitHub: `git push`, `gh api`)는 이번 세션에서 정상 동작했습니다. |
| DNS 문제 | 배제 | 이름 해석은 프록시가 담당하고, 거부는 정책 단계에서 났습니다. |
| TLS 인증서 문제 | 배제 | TLS 연결 전(CONNECT) 단계에서 거부되었습니다. `SSL_CERT_FILE`도 설정되어 있습니다. |
| 원격 서버 오류 | 해당 없음 (UNVERIFIED) | 원격까지 가지 않았습니다. |
| 인증 오류 / 요청 횟수 제한 / 응답 형식 변경 | 해당 없음 (UNVERIFIED) | 원격 응답을 받지 못해 판단할 수 없습니다. |

- **코드 측 사실 (CONFIRMED):**
  - `HttpFetcher._get_once`는 `httpx.TransportError`(ProxyError 포함)를 `FetchError("<예외명> while fetching host/path", retryable=True)`로 바꿉니다.
  - `get()`은 최대 2회 시도합니다. 따라서 실제 수집에서는 소스마다 프록시 거부가 2번씩 일어납니다.
  - 이전 Phase 5의 "전 소스 ProxyError"도 같은 원인으로 판단됩니다(당시 기록 `DevHub-2.0-Phase5-Status-and-Integration-Report.md` 22행).
- **실행 위치 (CONFIRMED):** 이 분석이 실행된 곳은 사용자 PC(KIST 망)가 아니라 Anthropic 클라우드 세션입니다.
  - 근거: 세션 정보 `environment_kind: anthropic_cloud`, `origin: web_claude_ai`, 호스트 `vm`, 기본 게이트웨이 192.0.2.1, 세션 전용 프록시 `127.0.0.1:33667`.
  - 따라서 위 403은 클라우드 환경의 출구 정책 때문이고, KIST 망과는 관계가 없습니다.
- **사용자 PC(KIST 망)에서 실행할 때 (UNVERIFIED, 별개 환경):** 다음 원인으로 다른 오류가 날 수 있습니다.
  - 기관 방화벽 차단 → 시간 초과·연결 오류
  - 필수 프록시 미설정
  - PAC·통합 인증 프록시 → 407 (httpx는 PAC·NTLM 미지원)
  - TLS 검사 장비 → `certificate verify failed` (기관 루트 인증서를 `SSL_CERT_FILE`로 지정. 검증 비활성화는 금지)
  - 사이트 분류 차단 → 일부 소스만 403
  - 진단 방법(DB 쓰기 없음): `env | grep -i proxy`, `curl -I <feed_url>`, `uv run python -m app.jobs collect --dry-run --source <slug>`. 오류 문구로 위 경우를 구분합니다.
- **결론:** 코드 결함이 아니라 실행 환경의 네트워크 정책입니다. 해결하려면 사용자가 환경의 Network access 설정에서 해당 호스트를 허용해야 합니다(12절). 우회는 하지 않았습니다.

## 7. 보안 · 안정성 · 데이터 품질 문제

### A. 안정성
| 항목 | 현황 | 판정 |
|---|---|---|
| 소스별 실패 격리 | `_run_locked`가 예외를 잡아 기록하고 다음 소스로 진행 | CONFIRMED (`test_collector.py::test_a_failing_source_is_recorded_and_does_not_stop_others`) |
| 타임아웃 | `collector_timeout_seconds=15` (연결·읽기 공통) | CONFIRMED (`config.py`) |
| 응답 크기 제한 | 스트리밍 5MB 상한 (`collector_max_response_bytes`) | CONFIRMED (코드). **테스트 없음** |
| 재시도·백오프 | 전송 오류·500/502/503/504에서 즉시 1회 재시도(총 2회). **백오프 없음**. 429와 `Retry-After`는 처리하지 않음. Stack Exchange `backoff` 필드 무시 | CONFIRMED (코드). 백오프·429는 **NOT IMPLEMENTED**. **테스트 없음** |
| 중복 수집 방지 | `UNIQUE(source_id, url_hash)`, 같은 피드 안의 중복 제거, 재수집 시 지표만 갱신 | CONFIRMED (`test_second_run_adds_nothing_and_only_refreshes_metrics`) |
| 동시 실행 방지 | 소스별 `GET_LOCK` → 두 번째 실행은 `skipped`로 기록 | CONFIRMED (`test_concurrent_run_of_the_same_source_is_skipped`) |
| 로그·오류 기록 | `job_runs`(상태·건수·오류 1000자), CLI 출력. `logging` 미사용 | CONFIRMED. 구조화 로그·알림은 NOT IMPLEMENTED |
| 저장 트랜잭션 | 소스별 1 트랜잭션(전부 저장 또는 전부 취소). 네트워크는 트랜잭션 밖 | CONFIRMED |
| 비정상 종료 | 프로세스가 죽으면 `job_runs.status='running'` 행이 남음(정리 로직 없음). 화면의 "마지막 갱신"은 성공 기록만 보므로 표시 영향은 없음 | CONFIRMED (코드). 정리 로직은 NOT IMPLEMENTED |
| 정기 실행 | 스케줄러 없음 | NOT IMPLEMENTED |

### B. 보안·접근 정책
| 항목 | 현황 | 판정 |
|---|---|---|
| SSRF | 요청 URL은 저장소 파일(`sources.yaml`, http/https만 허용: `taxonomy._http_url`)과 코드 상수(API 엔드포인트)뿐입니다. 사용자 입력 URL은 요청하지 않습니다. 웹 앱은 외부 요청을 하지 않습니다 | CONFIRMED |
| 리다이렉트 | `follow_redirects=True`. 횟수는 httpx 기본값(20)이고, **리다이렉트 대상 호스트·scheme·사설 IP 제한은 없습니다**. 피드 호스트가 악의적으로 바뀌면 내부 주소로 요청할 수 있습니다. 다만 응답은 피드로만 파싱되고 그대로 노출되지 않아 위험도는 낮습니다 | CONFIRMED (코드). 제한은 NOT IMPLEMENTED |
| API 키·비밀정보 | `STACKEXCHANGE_KEY`는 `SecretStr`. 오류 메시지에서 쿼리스트링을 제외합니다(`_where`) | CONFIRMED (`test_stackoverflow_decodes_titles_and_keeps_the_key_out_of_results`) |
| HTML·스크립트 | 저장 전에 요약·제목의 태그를 제거하고 평문으로 만듭니다. 화면(`ContentCard.jsx`)은 React 텍스트로 렌더링해 HTML로 해석하지 않습니다 | CONFIRMED |
| 링크 scheme | RSS는 http/https만 허용(`parse_feed` 92행). **Dev.to·HN·Stack Exchange 어댑터와 `store_items`는 scheme을 검증하지 않습니다.** 화면은 React 19.2의 `javascript:` URL 차단(`sanitizeURL`)으로 완화됩니다(심층 방어 부족) | CONFIRMED |
| 요청 빈도 | 실행당 소스별 1회(Dev.to 2회), 재시도 1회. 빈도는 실행 주기(스케줄러 없음)에 달림 | CONFIRMED |
| 저장·표시 범위 | 제목, 요약 300자, 링크, 작성자, 날짜, 지표. 본문은 저장하지 않음. 원문 링크로 이동 | CONFIRMED. 소스별 약관 적합성은 UNVERIFIED |

### C. 데이터 품질
| 항목 | 분석 | 판정 |
|---|---|---|
| 제목·요약만으로 태깅 가능한가 | 규칙 태거가 제목 + 요약 300자 + 소스 태그로 단어 일치(`Tagger.match`). 단어 경계·tag_only 별칭 처리는 테스트로 확인했지만, 실데이터 정확도는 측정한 적 없음 | 구조 CONFIRMED / 정확도 **UNVERIFIED** |
| 본문 부재에 따른 저하 | 예상: 제목에 기술명이 없는 기사(제품 출시, 사례 기사)는 누락(recall 저하). Stack Exchange·Dev.to는 소스 태그가 있어 영향이 적고, HN 링크 글과 국내 언론은 영향이 클 가능성 | UNVERIFIED (측정 필요) |
| HTML 본문 추출이 필요한가 | 필요하다고 전제하지 않습니다. 아래 비교와 8.3 측정 결과로 결정할 것을 제안합니다 | – |
| 출처별 같은 기사 중복 | 저장은 소스별(지표 보존), Home 화면에서 `url_hash`로 묶음. 정규화가 http/https, 끝 슬래시, Medium `?source=` 같은 변형을 같은 글로 보지 않음 | CONFIRMED (코드). 실데이터 영향 UNVERIFIED |
| 발행 시각·수집 시각 | 별도 컬럼, 정렬은 `COALESCE`. 피드가 날짜를 안 주면 수집 시각 | CONFIRMED |
| 뉴스·아티클·커뮤니티 분류 | 소스 단위 고정 분류(`kind`). 항목 단위 분류는 없음. InfoQ(news)처럼 개발 아티클 성격이 섞인 소스는 소스 단위로만 조정 가능 | CONFIRMED (설계상 한계) |

**RSS 요약만으로 충분한 경우와 본문이 필요한 경우**

| 용도 | 요약(현재)으로 충분한가 | 본문이 필요한가 |
|---|---|---|
| 목록 표시와 원문 링크 | 충분 | 불필요(저장하면 저작권·약관 위험) |
| 기술 필터·언급량(현재 기능) | 소스 태그가 있는 소스는 대체로 충분할 것으로 예상. 국내 언론은 불확실 | recall이 기준에 못 미칠 때만 검토 |
| Home·Dev 추천 근거(P5) | 측정 전에는 판단 불가 | 위와 같음 |
| 내부 요약 생성 | – | 요약을 만들려면 본문이 필요(미구현, 현재 요구 없음) |

**제안:**
1. 먼저 현재 방식으로 태깅 recall을 측정합니다(P5 설계 8.3).
2. 부족하면 본문 원문 요청 대신, 피드가 이미 주는 `content:encoded`를 **저장하지 않고 태깅에만 일시적으로 쓰는 방안**을 우선 검토합니다(추가 요청 없음, 약관 검토 필요).
3. 원문 HTML 추가 요청은 robots·약관·부하 검토가 필요해 마지막 선택지로 둡니다.

## 8. 개선 우선순위와 최소 수정안 (구현하지 않음)

| 등급 | 문제 | 근거 | 최소 수정안 |
|---|---|---|---|
| **P0** | 확인된 항목 없음 | 보안·데이터 손상·중대한 실행 장애를 일으키는 결함은 찾지 못했습니다 | – |
| **P1** | 26개 소스 모두 네트워크 정책으로 접근 불가 | 6절 | 코드 수정 없음. 사용자가 허용 호스트를 추가해야 함(12절) |
| **P1** | 정기 실행 수단 없음 → 지속 수집 불가 | 스케줄러 없음 | 최소안: 운영 환경의 cron(또는 예약 작업)이 `python -m app.jobs collect`를 호출하는 문서·설정. 앱 코드 변경은 불필요 |
| **P1** | 소스별 이용약관·robots 검토 미실시 | 5절 | 소스별 검토 표를 만들어 유지·제외 결정(사용자 판단) |
| **P2** | API 어댑터의 링크 scheme 미검증 | 7.B | `store_items`에서 http/https가 아닌 URL을 건너뛰고 테스트 1개 추가(약 10줄) |
| **P2** | 백오프·429·`Retry-After`·SE `backoff` 미처리 | 7.A | 재시도 사이 짧은 대기, 429를 재시도 대상에 넣고 `Retry-After` 상한 준수, SE `backoff` 값이 있으면 다음 실행까지 해당 소스 건너뛰기 기록 |
| **P2** | `HttpFetcher` 테스트 없음(재시도·크기·리다이렉트) | 테스트 검색 결과 0건 | `httpx.MockTransport`로 단위 테스트 4~5개 |
| **P2** | 리다이렉트 제한 없음 | 7.B | `max_redirects` 축소(예: 5), 리다이렉트 대상 scheme을 https/http로 한정, 사설·루프백 IP 거부(선택) |
| **P2** | 실데이터 태깅 품질 미측정 | 7.C | 표본 추출·라벨링·지표 계산 스크립트(읽기 전용) |
| **P2** | URL 정규화의 변형 미처리 | 7.C | 실데이터에서 변형 빈도를 측정한 뒤 결정(측정 전 수정하지 않음) |
| **P3** | `running`으로 남은 job_runs | 7.A | 다음 실행 시 오래된 `running` 행을 `failed`(중단)로 정리 |
| **P3** | 수집 로그 구조화·알림 | 7.A | `logging` 사용, 연속 실패 시 알림 |
| **P3** | `contents.summary`·`summary_status` 미사용 | 4절 | 쓰지 않을 거면 문서에 "예약 컬럼"으로 명시. 요약 기능은 별도 결정 |
| **P3** | 피드 본문을 태깅에만 일시 사용 | 7.C | recall 측정 후 필요할 때만 |

실수집 전에 **P2의 링크 scheme 검증, 백오프·429 처리, HttpFetcher 테스트, 리다이렉트 제한**을 먼저 반영할 것을 권장합니다. 모두 작은 범위이며, 기존 동작과 테스트를 바꾸지 않습니다.

## 9. Python · 직무 콘텐츠 검증 계획

### Python 2~5단원 (`docs/devhub-2.0/review/python-units-2-5/`, UNVERIFIED 유지)

| 검증 항목 | 방법 | 기준 자료 | 현재 |
|---|---|---|---|
| 설명·용어 정확성 | 단원별 문장을 공식 튜토리얼 해당 절과 대조. 용어는 한국어 공식 번역 용어를 우선 | docs.python.org/ko/3/tutorial (controlflow, datastructures) | UNVERIFIED (접속 차단) |
| 코드 실행 결과 | 예제·퀴즈 코드 실행, 주석 출력 비교 (`run_examples.py`, `verify_answers.py`) | Python 3.12 | CONFIRMED (29/29) |
| 버전 호환성 | 같은 스크립트를 지원 최소 버전(예: 3.10)과 최신(3.13)에서 실행. 버전 의존 문법(match 등) 사용 여부 점검 | 각 버전 인터프리터 | UNVERIFIED (3.12만 실행) |
| 퀴즈 정답 | 정답·오답 근거를 실행으로 확인. 문항의 모호성은 사람이 검토 | 위 스크립트 + 검토자 | 실행 CONFIRMED, 문항 검토 UNVERIFIED |
| 학습 순서 | 각 단원이 앞 단원에서 배운 개념만 쓰는지 점검(예: 2단원에서 리스트 미사용) | 단원 목차 대조 | 작성 시 반영, 독립 검토 UNVERIFIED |
| 초급자 난이도 | 문항별 난이도 표기(하/중/중상)를 검토자가 평가. 가능하면 실제 초급자 1~2명 시험 풀이 | 검토자 | UNVERIFIED |
| 링크 | 튜토리얼 URL이 열리는지, 안내한 절이 맞는지 | docs.python.org | UNVERIFIED |

→ 공식 문서 접속이 허용되거나 자료를 제공받기 전까지 UNVERIFIED를 유지하고, 정식 콘텐츠에는 반영하지 않습니다.

### 직무 6개 (`docs/devhub-2.0/review/careers/`, UNVERIFIED 유지)

| 검증 항목 | 방법 | 기준 자료 |
|---|---|---|
| 직무 설명·실제 업무 | 직무별 설명·대표 업무를 공식 직업 정보의 "하는 일·업무" 항목과 대조. 차이는 수정하거나 출처를 표시 | O*NET 직업 요약, 커리어넷·워크넷 직업 정보 |
| 핵심·관련 기술 | 공식 자료의 기술(Technology Skills 등) 목록과 대조. 기술 분류 slug로 매핑 가능한지 확인(예: SQL 항목 부재 → 분류 추가 여부 결정) | O*NET Technology Skills 등 |
| core/related 구분 | 공식 자료의 빈도·"핫 기술" 표시 등을 참고하되, 최종 판단 근거를 직무별로 기록 | 위 자료 + 검토자 |
| 직무·학습 연결 | 각 직무 core 기술에 공개 단원이 있는지 SQL로 측정. 없는 기술은 화면에 "학습 없음"으로 정직하게 표시(현재 구현) | DB 조회 |
| 공식 자료와의 대응 | O*NET 코드와 DevHub 직무의 대응(특히 DevOps·데이터 엔지니어·ML 엔지니어)을 확정하거나 "근사 대응"으로 표기 | 위 자료 |
| 미확인 설명 표시 | 근거가 없는 문장은 삭제하거나 "UNVERIFIED"로 표시해 서비스 반영에서 제외 | – |

## 10. 추가 학습 트랙 우선순위 (작성·공개하지 않음)

| 후보 | 연결 가능성 (기존 구조) | 사용자 가치 | 제작 비용 | 검증 난이도 | 평가 |
|---|---|---|---|---|---|
| **JavaScript 기초** | `javascript` 기술 있음. 프론트엔드 직무 core | 높음(웹 입문 수요, Home·Dev 언급 많을 것으로 예상) | 중 (Python 1~5와 같은 구조 재사용) | 중 (MDN 등 공식 문서, 접속 허용 필요) | **1순위** |
| **SQL 기초** | 기술 분류에 `sql` 없음 → 분류 추가 필요(현재 `database`/`postgresql`/`mysql`). 백엔드·데이터 직무 core | 높음(백엔드·데이터 직무 공통) | 중 | 중상 (DBMS별 문법 차이 → 기준 DB를 정해야 함. 예: 표준 SQL + MariaDB 실행 검증) | **2순위** (분류 결정 선행) |
| Git 기초 | `git` 있음. 여러 직무의 related | 중 (모든 개발자 공통) | 낮음 (단원 2~3개) | 낮음 (공식 Pro Git 문서) | 3순위 (작은 범위로 다양성 확보에 유리) |
| Linux/CLI 기초 | `linux` 있음. DevOps core | 중 | 중 | 중 | 4순위 |
| HTML/CSS | 분류에 해당 기술 없음(`frontend` 분야만) | 중 | 중 | 낮음 | 보류 (분류 추가 필요) |

- 8.2의 추천 다양성 관점에서는 Python 2~5 확정(+4단원)과 JavaScript(5단원)·Git(3단원)을 합치면, 공개 단원 13개 이상과 기술 3개 이상이 됩니다. SQL까지 추가하면 기술 4~5개로 잠정 목표에 근접합니다.
- 모든 트랙은 Python과 같은 절차(초안 → 실행 검증 → 공식 문서 대조 → 사용자 검토 → 별도 커밋)를 따릅니다.

## 11. P5 추천 설계 보완 결과

`docs/devhub-2.0/DevHub-2.0-P5-Feasibility-and-Design.md`에 **8절(P5-0 보완)**을 추가하고, 앞 절의 충돌 부분을 고쳤습니다.

| 요청 | 반영 |
|---|---|
| 1. 추천 종류별 선행 조건 분리 | 8.1: Career 단원 / 직무 기반 / Home·Dev를 각각의 조건·현재 상태로 분리. 서로 독립적으로 시작 가능 |
| 2. 15개·5개는 잠정 목표, 다양성으로 조정 | 8.2: "가상 프로필 20개 중 80%가 서로 다른 단원 2개 이상" 같은 다양성 측정으로 조정 |
| 3. precision + recall + 기술별 오탐·누락 | 8.3: 층화 표본, 기술별 P/R/F1, 오탐·누락 목록. 미달 기술은 추천 근거에서 제외 |
| 4. `confident`만으로 입문 단원 제외 금지 | 2.3 표와 4.2 규칙을 수정, 8.4 |
| 5. 목표·관심 우선순위 미확정 | 4.2 규칙 수정, 8.5 (초기값은 같은 등급) |
| 6. 완료 제외, 진행 중은 이어보기로 구분 | 8.6 (`continue_unit` 재사용) |
| 7. OFF·빈 프로필·후보 없음 분리 | 8.7 (기존 2.4 유지) |
| 8. 공개 API 정렬·응답 불변 | 8.8 |
| 9. 확인 가능한 근거로 이유 설명 | 8.9 (품질 미달 기술은 이유로 사용 금지) |
| 10. 읽기 전용, 학습·XP 무영향 | 8.10 (쓰기 SQL 0건 테스트) |

추천 기능과 P5-lite는 구현하지 않았습니다.

## 12. 실데이터 수집 전 사용자 승인 사항

| # | 승인·결정 | 내용 | 비고 |
|---|---|---|---|
| 1 | **네트워크 허용** | 환경 설정 → Network access → Allowed domains에 다음 호스트를 추가: `www.zdnet.co.kr`, `rss.etnews.com`, `www.itworld.co.kr`, `www.ciokorea.com`, `koreaittimes.com`(+리다이렉트 시 `www.koreaittimes.com`), `www.ddaily.co.kr`, `www.bloter.net`, `www.boannews.com`, `techcrunch.com`, `www.wired.com`, `www.theverge.com`, `feeds.arstechnica.com`, `venturebeat.com`, `feeds.infoq.com`, `rss.slashdot.org`, `dev.to`, `hn.algolia.com`, `api.stackexchange.com`, `feeds.feedburner.com`, `toss.tech`, `techblog.woowahan.com`, `tech.kakao.com`, `d2.naver.com`, `medium.com`, `tech.kakaopay.com`, `techblog.lycorp.co.jp`. 콘텐츠 검증용: `docs.python.org`, `www.onetonline.org`, `www.career.go.kr` | 사용자 조치. 리다이렉트로 다른 호스트가 필요하면 진단 결과로 추가 요청 |
| 2 | 소스별 이용약관·robots 검토 | 26개 소스의 RSS·API 이용 조건(재게시 범위, 요약 표시, 상업적 이용, 표기 의무: 특히 Stack Exchange CC BY-SA)을 검토하고 유지·제외 결정 | 허용 후 robots.txt·약관 페이지를 읽기 전용으로 확인해 표로 제출 가능 |
| 3 | 접근 진단 재실행 | 허용 후 같은 도구로 소스당 1회 요청해 상태·형식·파싱·필드 비율·요청 제한 헤더 확인(DB 쓰기 없음) | 승인 시 진행 |
| 4 | P2 보강을 먼저 할지 | 링크 scheme 검증, 백오프·429, HttpFetcher 테스트, 리다이렉트 제한 | 권장: 실수집 전에 반영 |
| 5 | 개발 DB 실수집 | `devhub_dev`의 `contents`·`content_technologies`·`job_runs`에 쓰기 발생. 주기(예: 하루 2회)·기간(2주)·실행 방법(수동 또는 cron) 결정 | 승인 필요. 실행 전 백업 |
| 6 | Stack Exchange 키 | 선택(하루 300 → 10,000회) | 비밀정보 관리 방식 결정 |
| 7 | 태깅 표본 라벨링 담당 | news·dev 각 200건 수작업 라벨 | 사용자 또는 지정 검토자 |
| 8 | 콘텐츠 검증 자료 | 네트워크 허용(1번) 또는 공식 자료 제공 | Python 2~5, 직무 6개 |
| 9 | 추가 트랙 착수 순서와 SQL 분류 추가 | 10절 | 결정 후 초안 작성 |
| 10 | 문서 커밋 | 이 보고서와 P5 설계서 보완의 문서 커밋 여부 | 미커밋 상태 |

---

### 부록: 이번 작업에서 실행한 것

| 작업 | 쓰기 여부 | 결과 |
|---|---|---|
| 코드·테스트·설정 정적 분석 | 없음 | 1~4, 7절 |
| 접근 진단 스크립트 (`probe_sources.py`, DB 미연결) | 없음 | 26회 요청, 모두 프록시 거부 |
| 프록시 상태 조회 | 없음 | `connect_rejected` 확인 |
| 개발 DB 읽기 전용 조회 (진단 전후 비교, 콘텐츠 현황) | 없음 | 전후 동일 |
| 문서 작성 | 저장소 문서만 (미커밋) | 이 보고서, P5 설계서 8절 |
