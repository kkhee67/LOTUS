# LOTUS 협업 지침
현재 계약 4.1-draft는 검토 초안이며 main 승인 전이다.
작업 전 README.md, docs/PROJECT.md, docs/OWNERSHIP.md, docs/GIT_WORKFLOW.md,
contracts/CONTRACT.md, contracts/INTERNAL_APIS.md와 담당 폴더 AGENTS.md를 읽는다.

- 건희: backend/의 서버·DB·API. 예원: frontend/ 화면과 API 연결.
- 시영: data_pipeline/, data/raw/, data/normalized/의 실제 데이터와 검증.
- 태환: recommender/의 AI 개발 및 별도 승인된 전체 통합.
- 이번 초기화 보완은 사용자 승인으로 태환이 기존 codex/bootstrap을 이어 맡는다.
  공통 모델·최소 골격·검사·인계 문서까지만 작성하며 타 담당 본개발은 하지 않는다.
- 초기화 이후 shared/, contracts/, 루트 의존성·CI 변경은 태환 조율과 건희 및 영향 담당자의 검토를 받는다.
- 한 브랜치는 한 작업자가 수정한다. main 직접 수정·push, 강제 push, 임의 reset/stash/삭제를 금지한다.
- 사용자 승인 범위에서만 commit/push/PR 생성한다. 작성자 외 팀원이 검토하고 사람이 병합한다.
- 프로필 원문·토큰·비밀키·DB·로그는 Git과 오류 응답에 남기지 않는다.
- 검사는 README의 명령을 사용하고 실패·미실행·미구현을 그대로 보고한다.
- 이번에는 외부 AI·추천 알고리즘·DB importer·실제 수집기·완성 UI를 구현하지 않는다.
- 팀원 첫 작업: docs/tasks/initial/{backend,frontend,data,ai}.md.
