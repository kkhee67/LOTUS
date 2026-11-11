# 예원 — 첫 프론트 작업
담당: frontend/의 사용자 화면과 API 연결.
서비스 목적: 경험이 부족한 청년이 상황·관심을 입력하면 실제 기회와 지원 전 확인 사항을 보고 원문으로 이동하도록 돕는다. 추천 이후 직무·활동·면접 안내를 별도 추가한다.

시작 전에 README.md, AGENTS.md, docs/PROJECT.md, docs/OWNERSHIP.md, docs/GIT_WORKFLOW.md,
contracts/CONTRACT.md, contracts/FIELDS.md, contracts/INTERNAL_APIS.md, docs/BOOTSTRAP_HANDOFF.md와 담당 폴더 AGENTS.md를 읽는다.
이번 초안은 main 검토·반영 후 기준 SHA를 확인하고 사용한다. 과거 대화나 별도 프롬프트를 알고 있다고 가정하지 않는다.
공통 계약은 shared/models, 필드 코드는 shared/catalog.json, 날짜는 shared/rules.py를 재사용한다.
공통 필드·의존성·CI 변경은 태환과 건희 및 영향 담당자 검토를 거친다.
사용자 개인정보·실제 비밀키는 테스트·로그·Git에 넣지 않는다.

## 수정 범위와 첫 작업
frontend/ 및 내부 테스트·의존성, 프론트 인계 문서. 첫 작업 하나는 **최소 프로필 입력 폼**이다.
생성 타입 frontend/src/generated/api.d.ts의 RecommendationRequest/UserProfile을 사용하며 별도 중복 모델을 만들지 않는다.
GET /api/v1/options로 선택지를 읽고 capabilities로 기능 사용 가능 여부를 표시한다.
개인화 입력은 POST /api/v1/recommendations 본문이다. 아직 비활성이므로 가짜 추천을 반환하지 않는다.
VITE_API_BASE_URL은 서버 origin만 받고 api-url.ts의 /api/v1 결합을 재사용한다.

## 완료 기준
- 전공·관심·희망 직무·목표 중 하나로 제출 요건 충족; 공백만 있는 값 거부.
- 선택 문자열 미입력은 생략/null, 활동 없음과 미입력 분리; 거주지·희망 근무지 분리.
- 프로필은 메모리에만 두고 URL·localStorage·로그에 저장하지 않음.
- 422 입력 오류, 503 미구현, 네트워크 오류를 구분. disabled 기능을 성공처럼 표시하지 않음.
- API 모의 응답으로 최소 입력·오류·상태 전환을 검사하되 실제 추천 결과와 혼동하지 않음.
- npm run check:generated, npm run typecheck, npm test, npm run build.

완성 결과 화면·공고 상세·관심 ID 저장은 별도 작업이다. 서버 응답의 원본 제목·URL을 사용한다.

## PR와 인계
origin/main을 확인하고 작은 codex/<role>/<task> 브랜치를 만든다. main 직접 수정·push 금지.
사용자 승인 범위에서만 커밋·push·PR 생성하며 다른 팀원이 검토하고 사람이 병합한다.
PR에 기준 SHA·계약 버전·구현 범위·실제 검사 명령/결과·미실행·다음 담당 연결 사항을 기록한다.
합성 테스트 성공과 실제 데이터·사이트 통합 성공을 구분한다. 미구현 기능을 빈 성공 응답으로 숨기지 않는다.
