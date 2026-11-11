# 시영 — 첫 데이터 작업
담당: data_pipeline/, data/raw/, data/normalized/의 수집과 검증.
서비스 목적: 경험이 부족한 청년이 상황·관심을 입력하면 실제 기회와 지원 전 확인 사항을 보고 원문으로 이동하도록 돕는다. 추천 이후 직무·활동·면접 안내를 별도 추가한다.

시작 전에 README.md, AGENTS.md, docs/PROJECT.md, docs/OWNERSHIP.md, docs/GIT_WORKFLOW.md,
contracts/CONTRACT.md, contracts/FIELDS.md, contracts/INTERNAL_APIS.md, docs/BOOTSTRAP_HANDOFF.md와 담당 폴더 AGENTS.md를 읽는다.
이번 초안은 main 검토·반영 후 기준 SHA를 확인하고 사용한다. 과거 대화나 별도 프롬프트를 알고 있다고 가정하지 않는다.
공통 계약은 shared/models, 필드 코드는 shared/catalog.json, 날짜는 shared/rules.py를 재사용한다.
공통 필드·의존성·CI 변경은 태환과 건희 및 영향 담당자 검토를 거친다.
사용자 개인정보·실제 비밀키는 테스트·로그·Git에 넣지 않는다.

## 수정 범위와 첫 작업
위 세 폴더와 내부 테스트·데이터 인계 문서. 첫 작업 하나는 **공개 공식 출처 한 곳의 자료 정규화**이다.
출처 접근 정책을 확인하고 학교 공지를 택하면 공개 접근 가능한 한 학교부터 시작한다.
모든 학교·출처의 수집이나 스케줄러까지 확대하지 않는다.
출력은 data/normalized/opportunities.json, sources.json, roles.json, resource_links.json의 UTF-8 배열이다.
공통 Opportunity/Source/RoleProfile/ResourceLink를 쓰고 shared.validation.validate_dataset으로 검증한다.
이번 범위에 없는 자료 배열은 []로 명확히 둔다. 합성 예시는 contracts/examples이며 실제 출력에 혼합하지 않는다.

## 완료 기준
- 실제 원문 URL·기관·게시일·checked_at·근거를 보존. 자료를 확인하지 않고 생성하지 않음.
- 인턴은 job subtype, 학교 채용도 job. ID는 재수집 시 안정적이며 중복을 방지.
- 자격 OR·예외·미해석 조건, experience_required=null을 보존.
- 날짜만 있으면 *_on, 정확한 시각이면 시간대 포함 *_at. 자격증 운영/회차 접수 분리.
- 수집 실패 시 이전 자료와 마지막 성공 시각 보존. 추천 요청 중 수집하지 않음.
- 공개 개인정보는 불필요하게 수집하지 않고 사용자 프로필을 테스트에 쓰지 않음.
- 실제 자료의 스키마·ID 참조 검사와 별도 synthetic/fixture 테스트. 누락·오류·반복 ID 검증.
- DB 직접 수정 금지. 건희에게 네 배열과 검증 결과·출처·확인 시각 인계.

공식 멘토링 사이트 링크는 ResourceLink이며 사람 매칭이나 최신 공고 수집 완료가 아니다.

## PR와 인계
origin/main을 확인하고 작은 codex/<role>/<task> 브랜치를 만든다. main 직접 수정·push 금지.
사용자 승인 범위에서만 커밋·push·PR 생성하며 다른 팀원이 검토하고 사람이 병합한다.
PR에 기준 SHA·계약 버전·구현 범위·실제 검사 명령/결과·미실행·다음 담당 연결 사항을 기록한다.
합성 테스트 성공과 실제 데이터·사이트 통합 성공을 구분한다. 미구현 기능을 빈 성공 응답으로 숨기지 않는다.
