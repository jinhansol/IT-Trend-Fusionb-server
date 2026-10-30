# DevHub 2.0 — E0 소스 이용 조건 검토 (AI 요약 PoC 후보)

- 확인일: **2026-10-30** (UTC 00:59 ~ 01:10, 클라우드 세션)
- 범위
  - TechCrunch, Dev.to, 국내 기술블로그 후보의 이용약관, robots.txt, API 정책, 저작권 안내를 읽기 전용으로 확인했습니다.
  - 기사와 블로그 글 본문은 요청하지 않았습니다.
  - LLM 호출, 코드 수정, DB 변경, commit/push는 하지 않았습니다.
- 관련 설계: `DevHub-2.0-News-Dev-Content-and-AI-Summary-Design.md` v2 (E0 단계)
- **이 문서는 법률 자문이 아닙니다.** 아래 "판단"은 약관 문구를 근거로 한 설계상 분류입니다. 최종 결정은 사용자가 합니다.

## 0. 결론 요약

| 소스 | RSS/API 접근 | 본문 접근·추출 | 본문 임시 처리·요약 표시 | 외부 LLM 전송 | PoC 적합성 |
|---|---|---|---|---|---|
| TechCrunch | 접근 가능. RSS 이용약관 있음 | **불가로 판단.** 약관에서 자동 추출을 금지(해석 필요)하고, robots.txt가 AI 크롤러를 전면 차단 | **불가로 판단.** 수정, 번역, 2차 저작물 작성 금지. RSS는 피드 내용을 "수정 없이" 표시하는 것만 허용 | **명시 조항 없음 → UNVERIFIED.** 다만 수정·2차 저작물 금지와 AI 크롤러 차단으로 보아 허용 근거 없음 | **부적합** |
| Dev.to | 접근 가능. API 이용약관은 **확인 실패**(문서 호스트가 허용 목록 밖) | 기술적으로는 가능(robots.txt는 글 경로를 막지 않음). 이용 조건은 사이트 약관상 제한적 | **불가로 판단(사이트 약관 기준).** 개인적·비상업적 일시 열람만 허용, 수정·복사·공개 표시 금지. API 약관이 달리 정하는지는 UNVERIFIED | **UNVERIFIED.** 허용 근거 없음 | **현재 부적합.** API 약관 확인 전 보류 |
| 국내 기술블로그 7곳 | **확인 실패.** 7개 호스트 모두 네트워크 허용 목록 밖(프록시 403) | 확인 실패 | 확인 실패 | 확인 실패 | **판단 불가.** 허용 목록 확장 필요 |

**PoC에 쓸 수 있다고 확인된 소스는 현재 0곳입니다.** 설계 v2의 E1과 E2는 이 상태로 시작할 수 없습니다. 진행 방안은 5절에 정리했습니다.

**기존 기능에도 영향이 있습니다.** 이미 구현된 수집·표시 기능(P2)에도 약관 문제가 있을 수 있습니다(4절).

---

## 1. 확인 방법과 요청 기록

| 요청 | 결과 | 비고 |
|---|---|---|
| `https://techcrunch.com/robots.txt` | 200 | SHA-256 앞 16자 `5fbefc8fdb1ded6f` |
| `https://techcrunch.com/` (홈) | 200 | 정책 페이지 링크를 찾는 용도. 링크만 추출 |
| `https://techcrunch.com/rss-terms-of-use/` | 200 | 본문 텍스트 `3d92b1d9930ee1da` |
| `https://techcrunch.com/terms-of-service/` | 200 | 본문 텍스트 `ad334fe0c6a5654d`. Effective date: May 1, 2025 |
| `https://dev.to/robots.txt` | 200 | `983a578c850154f6` |
| `https://dev.to/terms` | 200 | 본문 텍스트 `47d3b2f21068111e`. 개정일 표기 없음 |
| `https://dev.to/privacy` | 200 | `f655f6ed0aaf5dd9`. Last Updated: March 6, 2026 |
| `https://dev.to/code-of-conduct`, `https://dev.to/about` | 200 | 라이선스 관련 조항 없음 |
| `https://dev.to/api` | 301 → `https://developers.forem.com/api` | 리다이렉트 대상 호스트가 허용 목록 밖 → **API 문서·약관 확인 실패** |
| `https://dev.to/feed`, `https://techcrunch.com/feed/` | 200 | 상태 코드만 확인하고 응답 본문은 저장하지 않음(`-o /dev/null`) |
| 국내 기술블로그 7곳 `robots.txt` | **000 (프록시 CONNECT 403)** | 3절 |
| `https://developers.forem.com/api`, `https://legal.yahoo.com/` | **000 (프록시 CONNECT 403)** | — |

- 위 요청 외에 기사나 글 본문은 요청하지 않았습니다.
- 받은 정책 텍스트는 근거 보존용으로 scratchpad의 `e0/` 폴더에만 두었습니다. 저장소에는 넣지 않았습니다.
- 사용한 User-Agent는 `DevHub-policy-review/1.0`입니다.

---

## 2. 소스별 상세

### 2.1 TechCrunch (News, `techcrunch`)

#### 근거

| 문서 | URL | 핵심 문구 (원문 인용) |
|---|---|---|
| RSS Terms of Use | https://techcrunch.com/rss-terms-of-use/ | "If you choose to use a TechCrunch RSS feed, you are only permitted to display the content that is provided in the feed, with attribution to TechCrunch, and you must link to the full article on TechCrunch. You may not incorporate advertising into any TechCrunch RSS feed. You may not remove our attribution or links, **or otherwise modify our feed content.**" |
| Terms of Service (Effective May 1, 2025) | https://techcrunch.com/terms-of-service/ | "The Services are provided solely for your **personal noncommercial use**." / "unless explicitly authorized … you may not **modify, copy, reproduce, republish, upload, post, transmit, translate, sell, create derivative works**, exploit, or distribute in any manner or medium … any material from the Services." |
| 같은 문서 | 같음 | 금지 행위 목록: "Uses any automated or manual process, including but not limited to 'robots,' 'spiders,' 'scrapers,' or similar technologies, to monitor, **extract data from, copy**, or distribute any data from the Services" |
| 같은 문서 | 같음 | AP 기사: AP 자료를 "publish, display … rewrite … or redistribute" 금지, 개인적·비상업적 용도 외에는 컴퓨터 저장 금지 |
| robots.txt | https://techcrunch.com/robots.txt | `User-agent: *`에는 관리·검색 경로만 금지. 다음 AI 크롤러는 `Disallow: /` (사이트 전체 차단): `anthropic-ai`, `Claude-Web`, `ClaudeBot`, `GPTBot`, `ChatGPT-User`, `Google-Extended`, `CCBot`, `cohere-ai`, `Applebot-Extended`, `Bytespider`, `Diffbot`, `FacebookBot`, `omgili` |

**해석 필요:** "robots/spiders/scrapers" 금지 조항은 "you agree not to post, submit, or transmit any content or material … that:" 목록 안에 있습니다. 문법상 "게시하는 콘텐츠"에 대한 조항으로도 읽힙니다. 자동 수집 전반을 금지하는지는 해석이 필요합니다. 다만 아래 판단은 이 조항이 없어도 같습니다(수정·번역·2차 저작물 금지 조항 때문).

#### 항목별 판단

| 항목 | 판단 | 근거 |
|---|---|---|
| RSS 접근 | **가능, 조건부.** 피드 내용을 그대로 표시하고, TechCrunch 출처를 표시하고, 원문 링크를 제공해야 합니다. 광고를 삽입하거나 수정해서는 안 됩니다. | RSS Terms |
| 본문 접근·추출 | **불가로 판단.** HTML 본문 추출(B3)은 약관상 근거가 없고 자동 추출 금지 조항과 충돌합니다(해석 필요). 피드 본문(B1)은 피드에 본문이 있더라도 "그대로 표시"만 허용됩니다. | ToS, RSS Terms |
| 본문 임시 처리 | **불가로 판단.** 약관이 copy와 transmit을 명시적으로 금지합니다. 임시 처리가 이에 해당하는지는 법률 판단이지만, 허용 근거가 없습니다. | ToS |
| AI 요약 표시 | **불가로 판단.** 요약은 translate(한국어)이자 create derivative works이며, "modify our feed content"에도 해당합니다. | ToS, RSS Terms |
| 외부 LLM 전송 | **UNVERIFIED.** LLM에 관한 명시 조항은 없습니다. transmit 금지와 AI 크롤러 전면 차단은 AI 이용을 원하지 않는다는 명확한 신호로 봅니다. **robots.txt는 크롤러 접근 신호일 뿐 저작권 허락이 아니므로, 반대로 이를 허용 근거로도 쓰지 않습니다.** | ToS, robots.txt |
| 필요 조건(현재 메타데이터 표시) | TechCrunch 출처 표시 유지, 원문 링크 유지, 피드 내용 무수정 | RSS Terms |
| API | 공개 API 없음(해당 없음) | — |

**결론: AI 요약 PoC 대상에서 제외합니다.** 설계 v2의 `summary_level=none`, `body_level=none`, `llm_transfer=false`를 그대로 유지합니다.

### 2.2 Dev.to (Dev, `devto`)

#### 근거

| 문서 | URL | 핵심 문구 |
|---|---|---|
| Web Site Terms and Conditions of Use (개정일 표기 없음) | https://dev.to/terms | §2 Use License: "Permission is granted to temporarily download one copy of the materials … for **personal, non-commercial transitory viewing only**. … under this license you may not: **modify or copy the materials; use the materials for any commercial purpose, or for any public display (commercial or non-commercial)**; … remove any copyright or other proprietary notations …; or transfer the materials to another person or 'mirror' the materials on any other server." |
| 같은 문서 | 같음 | §7 Copyright: "Users agree and certify that they have rights to share all content that they post on DEV Community" (게시물에 대한 권리는 작성자가 보유함을 전제. DEV에 주는 라이선스 범위는 이 문서에 없음) |
| 같은 문서 | 같음 | §9: DEV 로고와 배지는 명시적 허락이 있어야 사용 가능 |
| robots.txt | https://dev.to/robots.txt | `User-agent: *`에 관리, 인증, 검색, 내부 API 일부(`/search/feed_content?`, `/async_info/base_data` 등)만 금지. 글 경로와 `/api/articles`는 금지하지 않음. AI 크롤러 개별 규칙 없음 |
| Privacy Policy (Last Updated March 6, 2026) | https://dev.to/privacy | 이용자 개인정보에 관한 문서. 콘텐츠 재사용이나 AI 관련 조항 없음 |
| API 문서·약관 | https://developers.forem.com/api (`dev.to/api`가 301로 연결) | **확인 실패.** 호스트가 네트워크 허용 목록 밖 |

#### 항목별 판단

| 항목 | 판단 | 근거 |
|---|---|---|
| API 접근 | **기술적으로 가능**(2.0 수집기 실측 성공). **이용 조건은 UNVERIFIED**(API 문서 확인 실패) | — |
| 본문 접근·추출 | robots.txt상 글 경로는 막혀 있지 않습니다. **그러나 robots 허용은 이용 허락이 아닙니다.** 사이트 약관은 복사를 금지합니다. API 상세 본문(B2)의 이용 조건은 UNVERIFIED | Terms §2, robots.txt |
| 본문 임시 처리 | **사이트 약관 기준으로 허용 근거 없음.** 허용 범위는 "개인적·비상업적 일시 열람"뿐입니다. | Terms §2 |
| AI 요약 표시 | **사이트 약관 기준 불가로 판단.** 수정 금지와 공개 표시 금지에 해당합니다. 글 저작권은 작성자에게 있다는 전제라서, 작성자 개별 허락 없이는 근거가 없습니다. | Terms §2, §7 |
| 외부 LLM 전송 | **UNVERIFIED.** 명시 조항이 없습니다. | — |
| 필요 조건 | 저작권 표기 제거 금지. DEV 로고는 허락이 필요. API 약관의 출처 표시 조건은 UNVERIFIED | Terms §2, §9 |

**결론: 현재 근거로는 PoC에 부적합합니다.** 다만 API 약관을 확인하지 못했으므로 **최종 판단을 보류**합니다. `developers.forem.com`을 허용 목록에 추가해 API 약관을 확인한 뒤 다시 판단합니다.

### 2.3 국내 기술블로그 (Dev, `sources.yaml` 등록 7곳)

| slug | 사이트 | 피드 (`sources.yaml`) | robots.txt 요청 | 정책 확인 |
|---|---|---|---|---|
| `toss-tech` | https://toss.tech/ | `/rss.xml` | **실패 (프록시 403)** | 확인 실패 |
| `woowahan-tech` | https://techblog.woowahan.com/ | `/feed/` | **실패** | 확인 실패 |
| `kakao-tech` | https://tech.kakao.com/ | `/feed/` | **실패** | 확인 실패 |
| `naver-d2` | https://d2.naver.com/ | `/d2.atom` | **실패** | 확인 실패 |
| `daangn-tech` | https://medium.com/daangn | `medium.com/feed/daangn` | **실패** | 확인 실패. Medium 약관도 적용됨 |
| `kakaopay-tech` | https://tech.kakaopay.com/ | `/rss` | **실패** | 확인 실패 |
| `lycorp-tech` | https://techblog.lycorp.co.jp/ko | `/ko/feed/index.xml` | **실패** | 확인 실패 |

- 7곳 모두 `curl: (56) CONNECT tunnel failed, response 403`이었습니다. 이는 클라우드 세션의 egress 허용 목록에 따른 거부입니다(P5-0 보고서 6절과 같은 원인).
- 사이트나 약관의 상태 때문이 아닙니다.
- **우회 접근은 시도하지 않았습니다.**

#### PoC 후보 제안 (확인 순서) [추정]

정책을 확인하지 못했으므로 **후보를 확정하지 않습니다.** 대신 허용 목록을 확장한 뒤 다음 순서로 확인할 것을 제안합니다.

| 순위 | 후보 | 이유 (모두 추정이며 확인 필요) |
|---|---|---|
| 1 | `woowahan-tech`, `kakao-tech` | • 자체 도메인이라 약관 계층이 하나입니다.<br>• 피드 경로 `/feed/`가 WordPress 형식과 같습니다. WordPress 피드는 흔히 `content:encoded`에 본문을 담으므로, 허용되면 HTML 요청(B3) 없이 피드 본문(B1)으로 PoC를 할 수 있을 가능성이 있습니다. 실제 포함 여부는 UNVERIFIED |
| 2 | `toss-tech`, `kakaopay-tech`, `naver-d2`, `lycorp-tech` | 자체 도메인. 피드 본문 포함 여부를 알 수 없음 |
| 제외 권고 | `daangn-tech` | Medium 플랫폼 약관과 블로그 운영사 정책이 겹쳐 검토 범위가 넓어집니다. |

**선정 기준 (허용 목록 확장 후 적용)**

1. 약관이나 저작권 안내가 **요약·2차 이용·자동 처리를 명시적으로 허용**하거나, 운영사가 **서면으로 허락**해야 합니다. robots.txt 허용만으로는 선정하지 않습니다.
2. 외부 LLM 전송을 금지하는 조항이나 AI 크롤러 차단 신호가 없어야 합니다. 없다고 해서 허용으로 간주하지는 않습니다. 이 경우 3번이 필요합니다.
3. 명시적 허용 조항이 없으면, **운영사에 문의해 받은 서면 허락**을 PoC 조건으로 둡니다.
4. 피드 본문(B1)이 있으면 우선합니다. HTML 요청이 필요 없기 때문입니다.

---

## 3. 네트워크 허용 목록 확장 필요

정책 확인을 위해 다음 호스트가 필요합니다. 설정은 사용자가 변경합니다.

| 목적 | 호스트 |
|---|---|
| Dev.to API 약관 | `developers.forem.com` |
| 국내 기술블로그 (robots, 약관, 피드) | `toss.tech`, `techblog.woowahan.com`, `tech.kakao.com`, `d2.naver.com`, `tech.kakaopay.com`, `techblog.lycorp.co.jp`, (당근을 검토할 경우) `medium.com`, `policy.medium.com` |
| 운영사 약관 페이지 (블로그 하단 링크에서 확인되는 호스트) | 블로그 접근 후 확정. 예상: 각 운영사 대표 도메인(`toss.im`, `woowahan.com`, `kakaocorp.com`, `navercorp.com`, `kakaopay.com`, `lycorp.co.jp` 등). **추정**이며, 실제 링크를 본 뒤 필요한 것만 요청합니다. |

- TechCrunch의 운영 모회사 정책 호스트(`legal.yahoo.com`)도 차단됐습니다. TechCrunch 자체 약관만으로 결론이 나므로 추가 확인은 필요 없습니다.

---

## 4. 기존 기능(P2 수집·표시)에 대한 발견 사항

E0 범위 밖이지만 확인 중에 드러난 위험입니다. 조치는 하지 않았고, 사용자 판단이 필요합니다.

| 소스 | 현재 동작 [코드] | 약관과의 관계 | 위험 |
|---|---|---|---|
| TechCrunch | RSS `summary`를 `plain_text`로 태그 제거 후 **300자로 잘라** 저장하고 카드에 표시. 출처 이름과 원문 링크는 표시함 | RSS Terms는 "그대로 표시 + 출처 + 원문 링크"를 허용하고 "modify our feed content"를 금지합니다. **태그 제거와 300자 절단이 "수정"에 해당하는지는 해석이 필요합니다.** | 중간. 대안: 피드 요약을 자르지 않고 표시하거나, 제목과 링크만 표시 |
| Dev.to | API 목록(제목, description ≤300자, 태그, 반응 수)을 공개 카드로 표시 | 사이트 약관 §2는 "public display" 금지. API 약관이 이를 허용하는지는 **UNVERIFIED** | API 약관 확인 전까지 판단 불가 |
| 공통 | DevHub의 상업성 여부가 약관 적용에 영향 | TechCrunch ToS와 Dev.to 약관 모두 비상업 조건을 둡니다. DevHub 운영 형태(개인 학습용, 비영리, 상업)는 확인하지 않았습니다. | 사용자가 정의해야 함 |

---

## 5. PoC 진행 방안 (선택지)

확인된 PoC 소스가 0곳이므로 다음 중 하나가 필요합니다.

| 안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| **A. 허용 목록 확장 후 재검토 (권장, 1단계)** | 3절의 호스트를 허용하고 E0를 다시 수행. 국내 블로그 7곳과 Forem API 약관 확인 | 현행 소스 목록 안에서 결정 | 명시적 허용 조항이 있는 소스가 없을 수 있음 |
| **B. 운영사 서면 허락** | 국내 블로그 1곳에 "본문 일시 처리, 외부 LLM 요약, 요약 표시"에 대한 허락을 요청 | 근거가 가장 명확함 | 시간이 걸리고 응답이 불확실함. 요청 주체는 사용자 |
| **C. 공개 라이선스 콘텐츠로 기술 PoC** | 2차 저작물과 재배포를 명시적으로 허용하는 라이선스(예: CC BY)의 기술 글만으로 E1/E2를 수행해 파이프라인과 품질 기준을 검증. 현재 `sources.yaml`에는 해당 소스가 없어 새로 찾아야 함 | 이용 조건 문제를 분리하고 기술 검증을 먼저 할 수 있음 | 실제 서비스 소스와 글 성격이 다를 수 있음. 출처 표시 조건 준수 필요 |
| D. 비공개 내부 평가로 강행 | 표시 없이 내부에서만 요약 | — | **권장하지 않음.** TechCrunch와 Dev.to 약관은 복사·수정 자체를 제한합니다. 공정 이용 여부는 법률 판단이며 이 검토로 정할 수 없습니다. |

**제안:** A를 먼저 하고, 그 결과로 B 또는 C를 고릅니다. News 쪽은 확인된 후보가 없습니다. TechCrunch를 대체할 언론 소스도 같은 절차가 필요합니다.

---

## 6. F2/E1 구현 체크리스트 추가 사항

같은 내용을 설계 문서 v2의 "12. 구현 체크리스트"에도 추가했습니다.

1. **같은 URL을 여러 소스가 제공하고 허용 정책이 다를 때**
   - 요약 대상 판단: 그룹 안에 `summary_level=body`이고 `llm_transfer=true`인 소스가 하나도 없으면 요약하지 않습니다.
   - 입력 소스: 허용된 소스의 경로(B1/B2/B3)로만 본문을 얻고, `input_source_id`에 기록합니다.
   - 표시 권한: 카드를 보여 주는 소스(News 대표 행 또는 Dev 행)와 입력 소스가 **둘 다** 현재 허용 상태일 때만 표시합니다.
   - 판단 필요: 요약이 원문 게시자의 기사에서 나왔다면, 카드 소스가 다르더라도 표시해도 되는지는 법률·정책 판단입니다. 기본값은 "둘 다 허용"입니다.
   - 테스트: 허용과 비허용이 섞인 그룹, 대표 행이 비허용 소스로 바뀌는 경우, 입력 소스의 허용 철회.
2. **기존 게시 가능한 요약을 유지하면서 재생성 상태를 관리하는 방법**
   - "현재 표시본"과 "재생성 시도" 상태를 분리합니다. 예: 표시 필드(`payload`, `generated_at`, `prompt_version` 등)와 시도 필드(`regen_status`, `regen_attempts`, `regen_next_at`, `regen_error`)를 나눕니다. 또는 시도용 행을 따로 두고 성공했을 때만 원자적으로 교체합니다.
   - 단일 `status` 컬럼으로 `done → pending`을 덮어쓰면 재생성 중에 기존 요약이 사라집니다. 이 방식은 금지합니다.
   - 무효화 사유(허용 철회, 품질 결함 버전)는 표시본 자체를 즉시 비표시로 만듭니다. 재생성 실패와는 구분합니다.
   - 테스트: 재생성 실패 시 기존 표시 유지, 성공 시 교체, 허용 철회 시 즉시 비표시, 동시 실행 시 한 번만 교체.
3. **E1 실험 코드의 SSRF 방어**
   - 실험 코드도 설계 v2 7.4절의 ①~⑥을 최소한 다음 수준으로 적용합니다.
     - `https`만 허용
     - 소스별 허용 호스트와 정확히 일치
     - IP 리터럴과 userinfo 거부
     - DNS 해석 결과가 공인 주소인지 확인
     - 리다이렉트를 수동으로 따라가며 매 홉 재검증(최대 3회)
     - 응답 크기 상한, 타임아웃, 쿠키 없음
   - 연결 주소 고정(DNS 재바인딩 대책)을 실험 코드에서 생략하면, 그 사실을 실험 보고서에 남깁니다.
   - 실험 코드도 허용된 소스 목록(E0 결과)에 없는 호스트에는 요청하지 않도록 **하드코딩된 허용 목록**을 둡니다.
   - 실험 시작 전에 사설 IP, 루프백, 오프사이트 리다이렉트, `http` 다운그레이드 사례를 단위 테스트로 확인합니다.

---

## 7. 사용자 승인·결정 필요 항목

| # | 항목 | 선택지 |
|---|---|---|
| 1 | TechCrunch를 AI 요약 대상에서 제외 | 승인 / 재검토 |
| 2 | 3절 호스트의 네트워크 허용 목록 추가(E0 재수행) | 전체 / 일부 / 보류 |
| 3 | PoC 진행 방안 | A → B / A → C / 기타 |
| 4 | DevHub 운영 형태 정의(개인 학습용, 비영리, 상업) | 사용자 정의 |
| 5 | 기존 기능 위험(4절) 대응: TechCrunch 요약 절단 표시, Dev.to 공개 표시 | Forem API 약관 확인 후 결정 / 즉시 조정 / 현행 유지 |
| 6 | 운영사 문의(B안)의 주체와 문안 | 사용자 |
| 7 | 이 보고서와 설계 문서의 커밋 | 승인 / 보류 |

**E0 보고서 제출 후 대기합니다.**
