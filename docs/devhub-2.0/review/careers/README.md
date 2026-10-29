# 초기 직무 6개 — 검토 자료

> **상태: 초안, UNVERIFIED, 사용자 검토 전.** 이 폴더는 로더 반영 대상이 아닙니다.
> 서비스 데이터 파일은 `backend/content/careers.yaml`이며 아직 만들지 않았습니다.
> 개발·테스트에서 직무 기능은 별도 테스트 데이터로 검증합니다:
> `backend/tests/career_helpers.py`, `backend/tests/fixtures/careers/e2e-careers.yaml`.

## 작성 방식과 검증 상태

- 설명, 대표 업무, 핵심·관련 기술은 AI(Claude)가 일반 지식으로 작성했습니다. **공식 자료와 대조하지 않았습니다.**
- 작성 환경의 네트워크 정책 때문에 근거로 삼으려던 사이트에 접속하지 못했습니다.
  - O*NET (`www.onetonline.org`, 미국 노동부 직업 정보)
  - 커리어넷 (`www.career.go.kr`)
- 참고 링크는 O*NET 직업 페이지 주소 형식으로 넣었지만, 열어 보지 못했습니다.
  - 직업 코드가 맞는지, DevHub 직무와 대응하는지 모두 미확인입니다.
- 연봉·채용 수요·성장률 같은 수치는 넣지 않았습니다.
- 형식 검증은 했습니다. 실제 `technologies.yaml`을 넣은 테스트 DB에서 `content_loader careers --dry-run`이 통과했습니다(6 created, 저장 안 함).

| 직무 | 설명 | 대표 업무 | 핵심 기술 (core) | 관련 기술 (related) | 참고 링크 |
|---|---|---|---|---|---|
| 백엔드 개발자 | UNVERIFIED | UNVERIFIED | backend, python, java, database — UNVERIFIED | spring, django, fastapi, nodejs, postgresql, mysql, redis, docker, git — UNVERIFIED | O*NET 15-1252.00 — 링크·대응 미확인 |
| 프론트엔드 개발자 | UNVERIFIED | UNVERIFIED | frontend, javascript, typescript, react — UNVERIFIED | nextjs, vue, angular, svelte, graphql, git — UNVERIFIED | O*NET 15-1254.00 — 링크·대응 미확인 |
| 데이터 분석가 | UNVERIFIED | UNVERIFIED | data, python, database — UNVERIFIED | postgresql, mysql, spark — UNVERIFIED | O*NET 15-2051.01 — 링크·대응 미확인 |
| 데이터 엔지니어 | UNVERIFIED | UNVERIFIED | data, python, database — UNVERIFIED | spark, kafka, postgresql, aws, gcp, docker — UNVERIFIED | O*NET 15-1243.00 — 대응 불확실 |
| DevOps·클라우드 엔지니어 | UNVERIFIED | UNVERIFIED | devops, cloud, linux, docker — UNVERIFIED | kubernetes, terraform, aws, azure, gcp, git — UNVERIFIED | O*NET 15-1244.00 — 대응 불확실 |
| 머신러닝 엔지니어 | UNVERIFIED | UNVERIFIED | ai, python, pytorch — UNVERIFIED | tensorflow, llm, data, docker — UNVERIFIED | O*NET 15-2051.00 — 대응 불확실 |

## 알려진 한계
- 기술 분류(`technologies.yaml`)에 SQL 항목이 없어서 `database`(분야)로 대신했습니다. 데이터 분석가는 SQL이 핵심인데, 분류에 SQL을 추가할지 검토가 필요합니다.
- 핵심 기술에 분야(`backend`, `data` 등)와 언어(`python` 등)가 섞여 있습니다. 직무 상세 화면에서 기술별 Career 학습 연결은 이 slug로 이루어집니다.
- 현재 공개 학습 단원은 Python 1단원(`python`)뿐이라, 대부분의 기술에 연결된 학습이 비어 있습니다.

## 확정 절차 (제안)
1. 네트워크 허용 목록에 근거 사이트를 추가하거나, 사용자가 근거 자료를 제공합니다.
2. 직무별로 설명·업무·기술을 근거와 대조해 수정하고, 이 문서의 상태를 항목별로 갱신합니다.
3. 사용자 승인 후 `backend/content/careers.yaml`로 옮기는 별도 커밋을 만듭니다(CI가 자동으로 로드 검증).
4. 개발 DB 반영은 0008 적용 승인 후 `content_loader careers`로 합니다.
