# 내부 함수 계약 4.1-draft
모두 동기 함수이며 shared.models를 import한다. recommend는 규칙 엔진이 구현됐고 나머지 세 함수는 FeatureUnavailableError를 발생시킨다.
백엔드가 DB에서 데이터를 읽고 aware datetime now와 함께 전달한다. AI는 DB·웹·현재 시각을 읽지 않는다.

```python
# recommender/opportunities/service.py
def recommend(request: RecommendationRequest, opportunities: list[Opportunity], *, now: datetime) -> RecommendationResponse: ...
# recommender/roles/service.py
def suggest_roles(request: RoleAdviceRequest, roles: list[RoleProfile], *, now: datetime) -> RoleAdviceResponse: ...
# recommender/roadmap/service.py
def make_plan(request: ActivityPlanRequest, roles: list[RoleProfile], opportunities: list[Opportunity], *, now: datetime) -> ActivityPlanResponse: ...
# recommender/interviews/service.py
def make_interview_guide(request: InterviewGuideRequest, roles: list[RoleProfile], opportunities: list[Opportunity], *, now: datetime) -> InterviewGuideResponse: ...
```

## 검증된 합성 입력 호출
저장소 루트에서 실행한다. 아래 호출의 try 블록에서 recommend 결과를 받는다. 예외 처리 예시는 미구현 후속 함수를 위한 것이다.

```python
from datetime import datetime
from shared.models import RecommendationRequest
from scripts.validate_examples import load, validate_examples
from recommender.opportunities.service import recommend
from recommender.errors import FeatureUnavailableError
request = RecommendationRequest.model_validate(load('recommendation_request.json')['request'])
opportunities = validate_examples()['opportunities']
try:
    result = recommend(request, opportunities, now=datetime.fromisoformat('2026-11-11T12:00:00+09:00'))
except FeatureUnavailableError:
    print('추천 알고리즘 미구현: 성공 결과가 아님')
```

입력·출력 형식: contracts/examples/recommendation_request.json, recommendation_response.json,
recommendation_api_response.json. 후속 기능은 role_advice.json, activity_plan.json, interview_guide.json.
응답 예시는 손으로 작성한 synthetic 계약 자료이며 알고리즘 실행·검증 결과가 아니다.
내부 응답을 백엔드가 받으면 전달한 원본 ID 목록에 있는지 검사하고 RecommendationApiItem으로 결합한다.
추가로 limit·candidate_count·정렬·허용 유형·참조를 검사해야 한다. 이 adapter는 backend/service_adapters.py에 구현했다.
직무 결과의 role_id/source_ids, 활동의 opportunity_id, 면접의 experience_ids도 전달 자료에 한정한다.
직무·활동·면접 기능은 독립적으로 실패 처리한다. 외부 AI는 현재 구현·호출하지 않는다.
