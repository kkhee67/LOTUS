# 공통 계약 4.1-draft — 검토 전
기존 실제 초안 4.0-draft를 보완한 버전이다. 승인 완료나 main 반영을 의미하지 않는다.
API 경로 버전 /api/v1과 계약 초안 버전은 독립적이다.

## 단일 기준과 필드
모델은 shared/models/__init__.py에 한 번 정의한다. 타입·필수·길이·기본값·null은
자동 생성 [FIELDS.md](FIELDS.md)와 [models.schema.json](models.schema.json)을 따른다.
추가 필드는 거부한다. 일반 문자열은 공백 제거 후 1~200자, 긴 설명은 1~4000자,
ID는 1~100자의 ASCII 안정 문자열이다. 목록 요소에도 빈 문자열을 허용하지 않는다.
공통 Texts는 최대 50, Ids는 최대 100개이며 개별 제한은 필드 명세에 있다.
선택 문자열은 null/생략=미입력, 빈 문자열은 오류. 생략 가능한 목록의 기본값은 빈 목록이다.
프로필 최소 입력은 major/interests/preferred_job_fields/goal 중 하나이다.
experience_status=provided이면 경험 목록이 반드시 있고 none/unknown이면 비어 있어야 한다.
none은 실제 없음, unknown은 미입력이다. 비학생에게 학년을 요구하지 않는다.
수업 프로젝트와 employment/internship의 kind를 별도로 보존한다.
전공과 자격상 허용 전공, residence_region과 preferred_job_regions는 서로 대체하지 않는다.

## 공고·출처·근거
공고 type은 contest/competition/job/certification/event/training/project/notice.
인턴은 job subtype, 설명회·박람회는 event subtype. 학교 게시 채용은 job이며 중복 notice를 만들지 않는다.
fields는 shared/catalog.json의 분야 코드, related_majors는 관련성 보조 단서이며 자격 제한이 아니다.
현재 분야 목록은 초안 4개이며 전 분야를 지원한다는 뜻이 아니다. 미지 분야를 임의 매핑하지 않는다.
Source는 출처, ResourceLink는 사이트/게시판/멘토링 링크이며 개별 공고를 대신하지 않는다.
source_kind=real/synthetic은 필수다. 실제 자료와 합성 자료를 한 데이터셋에 혼합하지 않는다.
Evidence의 id는 해당 공고 안에서 유일하며 field·사실 요약·http(s) 원문 URL을 보존한다.
자격 규칙과 추천 이유의 evidence_ids는 실제 공고 안의 ID만 참조한다.
experience_required는 명시 근거가 있을 때만 true/false, 없으면 null이다.
모든 source_ids는 sources.json에 있어야 하며 shared.validation.validate_dataset에서 검사한다.

## 자격 구조
EligibilityRule은 원문 요약·근거 ID·타입 제한 expression으로 구성한다. 임의 코드 실행은 없다.
- age: eq/gte/lte, 정수 0~120.
- text: school_id/major/residence_region 중 하나, in/not_in, 명시된 문자열 목록.
- education: in/not_in, 학적 enum 목록.
- all: 하위 조건 모두. any: 하위 조건 하나 이상.
- exception: base 또는 alternatives 중 하나를 충족하는 대체 경로. 기본 조건에서 예외를 제거하지 않는다.
최상위 eligibility_rules는 모두 필수이다. 표현할 수 없는 조건은 unresolved_conditions로 남긴다.
requirements_coverage=complete/partial/unknown으로 전체 파악 여부를 별도 기록한다.
미해석 조건이 있으면 complete를 허용하지 않는다. 조건 평가기는 이번에 구현하지 않았다.
미래 판정은 eligible(전체 필수 조건 충족 근거 충분)/ineligible(예외 없는 필수 불일치)/unknown으로 한다.
미확인을 지원 가능으로 바꾸지 않으며 eligible도 공식 지원 자격 보증이 아니다.
경력 기간 등 지원하지 않는 규칙은 임의 계산하지 않고 미해석 조건에 보존한다.

## 날짜
Asia/Seoul 기준. timestamp는 시간대 필수이며 원문 오프셋을 보존한다.
ApplicationInfo의 각 경계는 *_on(date) 또는 *_at(timestamp) 중 하나만 사용한다.
정확한 closes_at 시각부터 closed. closes_on만 있으면 다음 날 00:00부터 closed.
마감 당일에는 시각 확인 주의를 제공한다. 원문 closed 상태는 미래 날짜가 있어도 다시 열지 않는다.
접수 시작 전은 upcoming. upcoming의 명시된 시작 경계를 지나면 open으로 계산한다.
상태 unknown은 시작일 전후 모두 unknown을 보존하며 upcoming/open으로 확정하지 않는다. 끝난 마감은 closed로 계산한다.
기간 검증에서 날짜만 있는 시작은 Asia/Seoul 당일 00:00으로 계산한다. 정확한 마감은 시작보다 늦어야 한다.
날짜만 있는 마감은 그날 전체를 포함하므로 시작일과 같은 날이어도 유효하다. 원본 날짜·시각 정밀도는 변경하지 않는다.
shared.rules.application_state(application, *, now)는 aware now를 요구하며 원본을 수정하거나 현재 시각을 읽지 않는다.
자격증은 certification.status로 운영 상태를, exam_sessions[].application으로 접수를 표현한다.
회차가 없어도 active일 수 있으며 한 회차 종료가 자격증 종료를 뜻하지 않는다.
자격증의 일반 application은 unknown/날짜 없음으로 두고 회차를 사용한다.
게시 날짜·게시 시각은 둘 중 하나이며 행사일·접수일·checked_at과 구분한다.
checked_at은 마지막 자료 확인 시각이다. 자동 갱신이나 신선도를 보장하지 않는다.
초기 수집 자동화는 없으며 후속 수집기는 실패 시 이전 자료와 마지막 성공 시각을 보존한다.

## 추천·후속 기능
RecommendationRequest.types 생략 또는 []는 catalog의 모든 기회 유형, limit=8(1~20), 외부 AI 동의=false.
내부 결과는 공고 ID·판단만 담는다. 백엔드는 원본을 ID로 찾아 RecommendationApiItem에 결합한다.
결합 모델은 공고 ID와 근거 참조를 검사한다. 제목·기관·URL·날짜를 AI가 생성하지 않는다.
relevance_score는 0~100 정수, 합격 확률 아님. 정렬은 점수 내림차순 → eligible 우선 → ID 오름차순.
candidate_count는 필터·최소 관련성 통과 후 limit 이전 수. ineligible은 추천에서 제외한다.
현재 계산식·가중치·최소 관련성은 미구현이며 후속 AI 작업에서 문서화한다.
engine=rules와 template, 실제 LLM 사용 시에만 rules+llm/llm. 합성 응답 예시는 형식 자료이며 실행 결과가 아니다.
부가 기능은 RoleAdvice*, ActivityPlan*, InterviewGuide* 별도 모델을 사용한다.
일반 활동과 공고 연결 활동을 구분하고 면접 질문은 practice로 표시한다.
실제 사용자 경험 ID 외 참조·없는 경력·성과를 생성하지 않는다.

## API
| Method | 경로 (/api/v1 접두사) | 성공 모델 | 현재 상태 |
|---|---|---|---|
| GET | /health | HealthResponse | 구현 |
| GET | /options | OptionsResponse | 구현 |
| GET | /capabilities | 이름별 Capability | 구현 |
| GET | /opportunities | Page[Opportunity] | 503 |
| GET | /opportunities/{id} | Opportunity | 503 |
| GET | /resource-links | Page[ResourceLink] | 503 |
| POST | /recommendations | RecommendationApiResponse | 503 |
| POST | /career-roles | RoleAdviceResponse | 503 |
| POST | /activity-plan | ActivityPlanResponse | 503 |
| POST | /interview-guide | InterviewGuideResponse | 503 |
목록 limit 기본20/1~100, offset 기본0/0 이상. 응답 items,total,limit,offset.
개인화 입력은 POST 본문만 사용한다. 후속 구현에서 개별 항목 미존재는 404이다.
현재 저장소 미구현 상태에서 상세 조회는 404로 거짓 단정하지 않고 503을 반환한다.
capabilities는 사용자 기능 여섯 개를 표시하며 health/options/capabilities 자체는 기반 API이다.
FEATURES.json은 모든 해당 기능을 enabled=false/implemented=false로 기록하며 서버는 모순 설정을 거부한다.
오류는 {error:{code,message,details:[]}}. 404 NOT_FOUND, 422 VALIDATION_ERROR,
500 INTERNAL_ERROR, 503 FEATURE_UNAVAILABLE. 검증 오류에도 사용자 입력 원문을 반환하지 않는다.
잘못된 요청은 기능 미구현 여부보다 먼저 422로 거부할 수 있다.
OpenAPI는 실제 라우트·모델에서 생성한다. docs의 성공 스키마는 계약이며 구현 완료 표시가 아니다.

## 데이터와 DB 인계
출력은 UTF-8 배열: data/normalized/opportunities.json, sources.json, roles.json, resource_links.json.
합성 예시는 contracts/examples에만 둔다. 실제 normalized 파일은 아직 제공하지 않는다.
데이터 담당은 DB를 직접 수정하지 않는다. importer는 건희의 후속 작업이다.
전체 파일·ID 참조 검증 후 트랜잭션 반영, ID upsert, 반복 중복 방지, 오류 시 DB 보존,
입력에서 빠졌다고 자동 삭제 금지, real/synthetic 분리가 필수이다.
DB 구조 변경 시 마이그레이션·복구를 준비하며 DB 삭제로 해결하지 않는다.
수집은 추천 요청 중 실행하지 않으며 스케줄러가 검증되지 않았으므로 자동 갱신을 주장하지 않는다.
