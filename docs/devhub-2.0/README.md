# DevHub 2.0 설계·분석 문서

구현 전 검토 기록입니다. 작성 시점의 코드 기준이며, 이후 구현으로 내용이 달라질 수 있습니다.

| 문서 | 내용 |
| :--- | :--- |
| `DevHub-2.0-Phase5-Status-and-Integration-Report.md` | Phase 5(Home·Dev 수집) 구현 현황, Career 연계·개인화 가능성 |
| `DevHub-2.0-A-Policy-Technical-Impact-Report.md` | A안(사용자 상태·개인화) 기술 영향 감사 |
| `DevHub-2.0-A-v0.2-Architecture-Validation.md` | A안 v0.2 설계 검증 (판정: CONDITIONAL GO) |

## A안 v0.2 확정 결정 (2026-10-28)

- C-1: 학습 목표는 Career 성장 데이터. 개인화 ON일 때만 자동 추천에 활용, 개인화 초기화로 삭제하지 않음
- C-2: 학습자 유형별로는 정적 안내 문구·메뉴 링크만 허용. 콘텐츠 순위·추천 결과는 바꾸지 않음
- C-3: 이어보기는 기존 학습 진행 기록으로 구현. 별도 트랙 선택 기능은 보류
- C-4: 출처별 지표 보존을 위한 콘텐츠 중복 저장은 허용. 사용자 화면의 중복 노출은 별도 관리
- C-5: 트렌드 차트는 실제 성장세가 아닌 수집 콘텐츠의 기술 언급량으로 표시
- 학습자 유형은 권한 필드 `users.role`과 분리한 선택적 `learner_type`, 이후 변경 가능
