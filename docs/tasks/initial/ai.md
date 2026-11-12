# 태환 — 첫 AI 작업
담당: recommender/의 추천·진로 안내, 전체 통합은 별도 승인 작업.
서비스 목적: 경험이 부족한 청년이 상황·관심을 입력하면 실제 기회와 지원 전 확인 사항을 보고 원문으로 이동하도록 돕는다. 추천 이후 직무·활동·면접 안내를 별도 추가한다.

시작 전에 README.md, AGENTS.md, docs/PROJECT.md, docs/OWNERSHIP.md, docs/GIT_WORKFLOW.md,
contracts/CONTRACT.md, contracts/FIELDS.md, contracts/INTERNAL_APIS.md, docs/BOOTSTRAP_HANDOFF.md와 담당 폴더 AGENTS.md를 읽는다.
이번 초안은 main 검토·반영 후 기준 SHA를 확인하고 사용한다. 과거 대화나 별도 프롬프트를 알고 있다고 가정하지 않는다.
공통 계약은 shared/models, 필드 코드는 shared/catalog.json, 날짜는 shared/rules.py를 재사용한다.
공통 필드·의존성·CI 변경은 태환과 건희 및 영향 담당자 검토를 거친다.
사용자 개인정보·실제 비밀키는 테스트·로그·Git에 넣지 않는다.

## 재개 조건·수정 범위·첫 작업
공통 기반이 검토되어 main에 반영되고 사용자가 다음 진행을 요청한 뒤 시작한다.
recommender/ 및 내부 테스트, docs/recommender.md, docs/requests/recommender.md만 수정한다.
첫 작업 하나는 **외부 AI 없는 기본 추천**이다.
recommender/opportunities/service.py의 동기 함수:
recommend(request: RecommendationRequest, opportunities: list[Opportunity], *, now: datetime) -> RecommendationResponse.
현재 FeatureUnavailableError 골격을 구현으로 바꾸며 공통 모델을 재정의하지 않는다.
DB·웹·현재 시각 조회 없이 전달 자료만 사용하고 입력을 변경하지 않는다.

## 완료 기준
- 관심·희망 직무·목표 우선, 전공 보조. 학교 서열·나이로 능력을 점수화하지 않음.
- 활동 none/unknown과 거주지/희망 근무지를 구분; 없는 경력·기술·성과를 생성하지 않음.
- eligible/ineligible/unknown, OR·예외·미해석 조건 보존; 명확한 필수 불일치는 제외.
- shared.rules로 날짜 경계 처리; 자격증 운영과 회차를 분리.
- 점수 0~100 정수의 계산식·가중치·최소 관련성 문서화; 무관한 후보로 채우지 않음.
- 점수 내림차순 → eligible 우선 → ID 오름차순. candidate_count는 limit 전 후보 수.
- 실제 공고 evidence만 참조; 원문 제목·기관·URL·날짜를 재생성하지 않음.
- engine=rules, explanation_source=template. 외부 API 호출·비밀키 없이 실행.
- 고정 now로 최소 입력, 미지 분야, 관심/전공 불일치, 자격 3상태·OR·예외,
  마감 직전/정각/경과·날짜 마감, 자격증 회차 없음/종료, 빈 후보, 정렬·limit·점수,
  입력 불변·결정성·ID/근거 참조·동의 없음·외부 호출 없음을 검사.
- 함수 단위 테스트와 기존 bootstrap 검사를 실행하고 백엔드 호출 예·규칙·미완료를 인계.

직무·활동·면접·외부 AI·전체 통합은 이번 첫 추천 작업에 포함하지 않는다.

## PR와 인계
origin/main을 확인하고 작은 codex/<role>/<task> 브랜치를 만든다. main 직접 수정·push 금지.
사용자 승인 범위에서만 커밋·push·PR 생성하며 다른 팀원이 검토하고 사람이 병합한다.
PR에 기준 SHA·계약 버전·구현 범위·실제 검사 명령/결과·미실행·다음 담당 연결 사항을 기록한다.
합성 테스트 성공과 실제 데이터·사이트 통합 성공을 구분한다. 미구현 기능을 빈 성공 응답으로 숨기지 않는다.
