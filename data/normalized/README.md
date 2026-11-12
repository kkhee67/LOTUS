# 정규화 출력 위치

단국대학교 채용공지 첫 배치의 UTF-8 JSON 배열이다.

- `sources.json`에는 채용 게시판 출처가 있다.
- `opportunities.json`에는 원문과 근거를 확인한 채용 공고 3건이 있다. 이 중 1건은 접수가 끝난 사례다.
- `roles.json`과 `resource_links.json`은 이번 범위에서 빈 배열이다.

[데이터 작업 안내](../../data_pipeline/README.md)의 명령으로 생성하고
`shared.validation.validate_dataset`을 통해 검증한다.
건희에게 인계할 파일과 원문 확인 범위는 [인계 문서](../../data_pipeline/HANDOFF.md)에 기록한다.
