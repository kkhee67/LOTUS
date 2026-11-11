# 건희 — 첫 백엔드 작업
담당: backend/의 서버·DB·API. 초기화를 다시 하지 말고 현재 기반에서 서버·DB 작업을 이어간다.
서비스 목적: 경험이 부족한 청년이 상황·관심을 입력하면 실제 기회와 지원 전 확인 사항을 보고 원문으로 이동하도록 돕는다. 추천 이후 직무·활동·면접 안내를 별도 추가한다.

시작 전에 README.md, AGENTS.md, docs/PROJECT.md, docs/OWNERSHIP.md, docs/GIT_WORKFLOW.md,
contracts/CONTRACT.md, contracts/FIELDS.md, contracts/INTERNAL_APIS.md, docs/BOOTSTRAP_HANDOFF.md와 담당 폴더 AGENTS.md를 읽는다.
이번 초안은 main 검토·반영 후 기준 SHA를 확인하고 사용한다. 과거 대화나 별도 프롬프트를 알고 있다고 가정하지 않는다.
공통 계약은 shared/models, 필드 코드는 shared/catalog.json, 날짜는 shared/rules.py를 재사용한다.
공통 필드·의존성·CI 변경은 태환과 건희 및 영향 담당자 검토를 거친다.
사용자 개인정보·실제 비밀키는 테스트·로그·Git에 넣지 않는다.

## 수정 범위와 첫 작업
backend/ 및 내부 테스트, docs/backend.md. 첫 작업 하나는 **SQLite 정규화 자료 importer**이다.
조회 API나 추천 adapter까지 한 PR에 확장하지 않는다. DB 파일은 runtime/에 두고 Git에 넣지 않는다.
데이터 담당의 네 UTF-8 JSON 배열을 shared.models의 Source/Opportunity/RoleProfile/ResourceLink로 읽고
shared.validation.validate_dataset을 호출한 뒤 트랜잭션으로 반영한다.

## 완료 기준
- 전체 입력과 ID 참조를 검증한 후 ID 기준 추가·갱신; 두 번 입력해도 중복 없음.
- 잘못된 파일이나 참조가 있으면 기존 DB와 이미 반영된 자료를 보존.
- 파일에 없는 기존 항목을 자동 삭제하지 않음. real/synthetic 혼합 거부.
- schema 변경 마이그레이션과 복구 방법; 개인정보 프로필 저장 없음.
- 임시 DB+합성 자료 테스트로 반복 입력·부분 오류·갱신·기존 자료 보존 검사.
- python -m pytest backend/tests tests/integration -q, python -m scripts.check_generated.

이후 별도 작업: 조회 API(Page[Opportunity], Opportunity, Page[ResourceLink]) → recommend adapter.
adapter는 RecommendationResponse ID를 실제 원본과 결합해 RecommendationApiResponse로 반환한다.
implemented/enabled는 실제 구현·검증 후에만 공통 검토로 변경한다.

## PR와 인계
origin/main을 확인하고 작은 codex/<role>/<task> 브랜치를 만든다. main 직접 수정·push 금지.
사용자 승인 범위에서만 커밋·push·PR 생성하며 다른 팀원이 검토하고 사람이 병합한다.
PR에 기준 SHA·계약 버전·구현 범위·실제 검사 명령/결과·미실행·다음 담당 연결 사항을 기록한다.
합성 테스트 성공과 실제 데이터·사이트 통합 성공을 구분한다. 미구현 기능을 빈 성공 응답으로 숨기지 않는다.
