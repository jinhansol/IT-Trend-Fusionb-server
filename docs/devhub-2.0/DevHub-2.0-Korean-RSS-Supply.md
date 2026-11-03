# DevHub 2.0 — 국내 RSS 공급원 검증과 수집 안전장치

작성일: 2026-11-03. 기준: 기존 `HttpFetcher`·RSS 어댑터, `content/sources.yaml`.

## 1. 요약

- 기술 검증: 국내 36곳(주소 46개)을 robots.txt 확인 후 1회씩 요청했다. 파싱 성공은
  News 8곳, Dev 16곳이다(카카오페이는 형식은 정상이나 0건).
- 운영 승인: **0곳**. 기술적으로 읽히는 것과 이용 허락은 별개이며, 이용 조건이 확인된
  곳은 최근 글이 없는 CC BY 4.0 개인 블로그뿐이다.
- 안전장치: `options.terms: approved`가 아닌 소스는 `collect`가 저장하지 않고 정기 수집도
  하지 않는다. 소개문은 `options.excerpt: true`인 소스만 API로 내보낸다. 수집, `--dry-run`,
  `diagnose` 모두 RSS 요청 전에 robots.txt를 확인한다.

## 2. 명령별 동작

| 명령 | 대상 | DB 저장 | robots.txt |
|---|---|---|---|
| `collect` | active이면서 terms approved | 예 | 확인 |
| `collect --source SLUG` | 같은 조건. paused·미승인은 `refused`로 표시만 | 예 | 확인 |
| `collect --group news\|dev` | `collect-schedule.yaml` 목록 중 위 조건 충족 | 예 | 확인 |
| `collect --dry-run` | active (지정 시 paused 포함) | 아니오 (job_runs도 없음) | 확인 |
| `diagnose [--source\|--group]` | `sources.yaml` 전체 (DB 불필요) | 아니오 | 확인 |
| cron | `collect --group` | 위와 같음 | 확인 |

`refused`는 요청도 기록도 하지 않는다. 기존 DB 행에 `terms`가 없으면 미승인으로 읽힌다.

robots.txt 해석은 RFC 9309를 따른다. 4xx, HTML 응답, http로의 리다이렉트는 "규칙 없음"으로
허용하고, 5xx나 연결 실패는 해당 호스트를 요청하지 않는다.

## 3. 소스 승인 절차

1. `python -m app.jobs diagnose --source SLUG`로 접근·파싱·공급량 확인.
2. 운영사의 공식 약관 또는 서면 허락으로 제목·출처·날짜·링크 표시 범위 확인.
3. `sources.yaml`에서 해당 소스에 `options: { terms: approved }`, 필요하면 `status: active`.
   소개문 표시까지 허락되면 `excerpt: true`, AI 요약은 별도 근거가 있을 때만 `ai_summary: true`.
4. 정기 수집이 필요하면 `collect-schedule.yaml`의 그룹 `sources`에 추가하고 crontab을 다시 만든다.

## 4. 소스별 상태 (2026-11-03 측정, `diagnose`)

### News (Home)

| slug | 상태 | 피드 | 7일 | 1회 수집 범위 | 이용 조건 근거 |
|---|---|---|---|---|---|
| zdnet-korea | active | FeedBurner, 30건 | 30 | 약 14시간 (12시간 주기 시 누락 위험) | 회원 약관 제9조: 사전 동의 없는 발췌·인용 후 링크 금지 |
| etnews | active | SW 섹션 `04.xml`, 50건 | 50 | 약 20시간 | 사전 허가 필요(콘텐츠 구매 안내), 세부 미확인 |
| bloter | active | CDN 주소, 50건 | 50 | 약 19시간 | 저작권보호정책: 승낙 없는 복제·전송·배포·변형 금지 |
| boannews | active | `/rss/allArticle.xml`, 50건 | 50 | 약 24시간 | 블로터와 같은 조항 |
| aitimes | paused 후보 | 50건 | 50 | 약 21시간 | 블로터와 같은 조항 |
| boho-notice | paused 후보 | 10건, 소개문 없음 | 10 | 약 72시간 | RSS 안내: 공개 콘텐츠 구독 제공. 재노출 조건 미확인 |
| itworld-korea | paused | — | — | — | robots.txt `Disallow: /feed/` |
| ciokorea | paused | 404 | — | — | 한국어 `/kr/feed/`는 robots.txt 금지 |
| ddaily | paused | 홈으로 리다이렉트 | — | — | 공식 RSS 없음 |

블로터는 IT 외 기사(부동산·금융·부고) 비중이 높고, ZDNet은 자동차·바이오 기사가 많다.

### Dev

| slug | 상태 | 7일 / 30일 | 최신 | 비고 |
|---|---|---|---|---|
| geeknews | active | 20 / 20 | 11/3 | 20건이 약 8시간. 6시간 주기는 빠듯함. 약관은 과부하 자동 접근만 금지 |
| toss-tech | active | 1 / 10 | 10/27 | |
| naver-d2 | active | 4 / 10 | 11/2 | robots.txt가 http NotFound로 리다이렉트(규칙 없음) |
| kakao-tech | active | 1 / 4 | 10/27 | 하단 Terms는 카카오 서비스 운영정책(블로그 이용 허락 아님) |
| daangn-tech | active | 0 / 3 | 10/21 | Medium 약관 미확인 |
| lycorp-tech | active | 0 / 2 | 10/26 | |
| kakaopay-tech | active | 0 / 0 | — | 피드 0건 |
| kurly-tech | paused 후보 | 1 / 1 | 11/3 | 홈페이지가 안내하는 `/rss.xml` (기존 `feed.xml`은 403) |
| outsider-blog | paused 후보 | 1 / 4 | 11/1 | 홈페이지가 안내하는 `/atom` (기존 `/rss`는 404) |
| woowahan-tech | paused | — | — | Cloudflare 403, 우회하지 않음 |

모든 기업 블로그는 "All Rights Reserved"로 표시되며 재게시 조건은 미확인이다.

### 등록하지 않은 후보

- 뱅크샐러드, 인프랩, 데브시스터즈, 44BITS: 파싱은 되지만 최근 공급이 적다.
- CC BY 4.0 개인 블로그 4곳: 최근 30일 신규 글이 0건이다.
- 과기정통부·행안부: IT 비중이 낮다.
- KISA: 서버 인증서 체인 불완전.
- 저작권위원회: HTTP 202 응답.
- jojoldu: 451. WikiDocs: Cloudflare challenge.

## 5. 수정한 수집기 결함

- **게시일:** `2026.11.02` 형식의 pubDate를 feedparser가 모든 항목에 대해 2026-11-01로 잘못
  읽었다(과기정통부). 이 형식은 직접 읽고, 하루 넘게 미래인 날짜는 버린다. 날짜가 없으면
  `published_at`은 NULL로 두며 수집 시각으로 채우지 않는다. 정렬만 `sort_at`(COALESCE)을 쓴다.
- **빈 응답:** 0바이트 응답이 `AttributeError`로 실패하던 것을
  `FetchError: not a readable RSS/Atom feed (empty response)`로 바꿨다. 다른 소스에는 영향이 없다.
- **응답 크기:** 상한 5MB는 유지한다. 데브시스터즈 4.0MB, 인프랩 3.8MB(본문 전체 포함 피드)는
  현재 상한 안이다. 넘으면 해당 소스 전체가 실패로 기록되며, 일부만 저장되는 일은 없다.
  두 곳 모두 등록하지 않았다.
- **HTTP 202:** 저작권위원회 피드는 202 Accepted와 함께 XML 3건을 준다. 202는 "처리 중"이라는
  뜻이라 완전한 응답이라는 보장이 없으므로 계속 거부한다.

## 6. 남은 일

- 운영사 이용 허락 확인. 우선순위:
  - News: 전자신문, 보안뉴스, AI타임스, 보호나라.
  - Dev: GeekNews, 토스, D2, 카카오, LY.
- ZDNet은 사전 동의가 없으면 활성화하지 않는다.
- 소스별 수집 간격(ZDNet 6시간, GeekNews 3~4시간, 블로그 하루 1~2회)은 현재 그룹 단위
  스케줄로는 표현할 수 없다. 소스를 승인할 때 함께 결정한다.
