# AI 내부 함수 — 검토 초안
모두 동기 함수. shared 모델 import, DB·웹 직접 접근 없음, now는 시간대 포함 datetime.
아래 경로·서명은 제안이며 아직 구현/모델 전체가 존재하지 않는다.
- recommender/opportunities/service.py: recommend(request: RecommendationRequest, opportunities: list[Opportunity], *, now: datetime) -> RecommendationResponse
- recommender/roles/service.py: suggest_roles(request: RoleAdviceRequest, roles: list[RoleProfile], *, now: datetime) -> RoleAdviceResponse
- recommender/roadmap/service.py: make_plan(request: ActivityPlanRequest, roles: list[RoleProfile], opportunities: list[Opportunity], *, now: datetime) -> ActivityPlanResponse
- recommender/interviews/service.py: make_interview_guide(request: InterviewGuideRequest, roles: list[RoleProfile], opportunities: list[Opportunity], *, now: datetime) -> InterviewGuideResponse
백엔드는 원본 자료와 now를 전달하고 결과의 ID·근거·형식을 검증한다.
