"""HTTP adapters only; algorithms remain owned by the recommender package."""
from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from backend.catalog_store import CatalogUnavailable, read_catalog
from backend.responses import error_response as query_error
from backend.settings import Settings
from recommender.errors import FeatureUnavailableError
from recommender.opportunities import service as opportunity_engine
from recommender.roles import service as role_engine
from recommender.roadmap import service as roadmap_engine
from recommender.interviews import service as interview_engine
from shared.models import (
    ActivityPlanRequest, ActivityPlanResponse, InterviewGuideRequest, InterviewGuideResponse,
    Page, RecommendationApiItem, RecommendationApiResponse, RecommendationRequest,
    RecommendationResponse, ResourceLink, RoleAdviceRequest, RoleAdviceResponse,
)


def validated_result(model, value):
    # Revalidate even model instances: engines can mutate already validated objects.
    return model.model_validate(value.model_dump() if hasattr(value, 'model_dump') else value)


def assemble_recommendations(request, opportunities, *, now):
    """Combine validated engine IDs with untouched DB originals, never generated facts."""
    originals = {item.id: item for item in opportunities}
    result = validated_result(RecommendationResponse, opportunity_engine.recommend(
        request.model_copy(deep=True), [item.model_copy(deep=True) for item in opportunities], now=now))
    candidates = [item for item in opportunities if not request.types or item.type in request.types]
    if (result.candidate_count > len(candidates)
            or len(result.items) != min(request.limit, result.candidate_count)):
        raise ValueError('Invalid recommendation counts')
    expected = sorted(result.items, key=lambda item: (
        -item.relevance_score, item.eligibility != 'eligible', item.opportunity_id))
    if result.items != expected:
        raise ValueError('Invalid recommendation order')
    if not request.allow_external_ai and result.engine != 'rules':
        raise ValueError('External explanations were not authorized')
    items = []
    allowed = {item.id for item in candidates}
    for item in result.items:
        if item.opportunity_id not in allowed:
            raise ValueError('Unknown or disallowed opportunity')
        items.append(RecommendationApiItem(
            recommendation=item, opportunity=originals[item.opportunity_id]))
    return RecommendationApiResponse(items=items, candidate_count=result.candidate_count,
                                     engine=result.engine, warnings=result.warnings)


def validate_guidance(feature, request, result, dataset):
    roles = {item.id: item for item in dataset['roles']}
    opportunities = {item.id for item in dataset['opportunities']}
    if feature == 'career-roles':
        result = validated_result(RoleAdviceResponse, result)
        ids = [item.role_id for item in result.items]
        if len(ids) != len(set(ids)) or len(ids) > request.limit:
            raise ValueError('Invalid role count')
        for item in result.items:
            if item.role_id not in roles or not set(item.source_ids) <= set(roles[item.role_id].source_ids):
                raise ValueError('Invalid role reference')
    elif feature == 'activity-plan':
        result = validated_result(ActivityPlanResponse, result)
        allowed = set(request.opportunity_ids) if request.opportunity_ids else opportunities
        if any(step.opportunity_id is not None and step.opportunity_id not in allowed
               for step in result.steps):
            raise ValueError('Invalid plan reference')
    else:
        result = validated_result(InterviewGuideResponse, result)
        allowed = (set(request.experience_ids) if request.experience_ids
                   else {item.id for item in request.profile.experiences})
        if any(not set(item.experience_ids) <= allowed for item in result.questions):
            raise ValueError('Invalid experience reference')
    return result


def create_service_router(settings: Settings, *, enabled: Callable[[str], bool],
                          clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
    router = APIRouter(prefix='/api/v1')

    def run(feature, request):
        if not enabled(feature):
            return query_error(503, 'FEATURE_UNAVAILABLE', '해당 기능이 비활성 상태입니다.')
        try:
            dataset = read_catalog(settings)
            now = clock()
            if feature == 'recommendations':
                return assemble_recommendations(request, dataset['opportunities'], now=now)
            role_ids = {item.id for item in dataset['roles']}
            opportunity_ids = {item.id for item in dataset['opportunities']}
            if (not set(getattr(request, 'role_ids', [])) <= role_ids
                    or not set(getattr(request, 'opportunity_ids', [])) <= opportunity_ids):
                return query_error(404, 'NOT_FOUND', '연결할 자료를 찾을 수 없습니다.')
            profile_request = request.model_copy(deep=True)
            roles = [item.model_copy(deep=True) for item in dataset['roles']]
            opportunities = [item.model_copy(deep=True) for item in dataset['opportunities']]
            # Restrict selected context before passing it to the owned implementation.
            if getattr(request, 'role_ids', []):
                roles = [item for item in roles if item.id in request.role_ids]
            if getattr(request, 'opportunity_ids', []):
                opportunities = [item for item in opportunities if item.id in request.opportunity_ids]
            if feature == 'career-roles':
                result = role_engine.suggest_roles(profile_request, roles, now=now)
            elif feature == 'activity-plan':
                result = roadmap_engine.make_plan(profile_request, roles, opportunities, now=now)
            else:
                result = interview_engine.make_interview_guide(profile_request, roles, opportunities, now=now)
            return validate_guidance(feature, request, result, dataset)
        except (CatalogUnavailable, FeatureUnavailableError):
            return query_error(503, 'FEATURE_UNAVAILABLE', '자료 또는 기능을 이용할 수 없습니다.')
        except Exception:
            # Do not log engine errors: they may contain profile or source text.
            return query_error(500, 'INTERNAL_ERROR', '요청을 처리할 수 없습니다.')

    @router.post('/recommendations', response_model=RecommendationApiResponse)
    def recommendations(request: RecommendationRequest):
        return run('recommendations', request)

    @router.post('/career-roles', response_model=RoleAdviceResponse)
    def career_roles(request: RoleAdviceRequest):
        return run('career-roles', request)

    @router.post('/activity-plan', response_model=ActivityPlanResponse)
    def activity_plan(request: ActivityPlanRequest):
        return run('activity-plan', request)

    @router.post('/interview-guide', response_model=InterviewGuideResponse)
    def interview_guide(request: InterviewGuideRequest):
        return run('interview-guide', request)

    @router.get('/resource-links', response_model=Page[ResourceLink])
    def resource_links(limit: int = Query(default=20, ge=1, le=100),
                       offset: int = Query(default=0, ge=0)):
        if not enabled('resource-links'):
            return query_error(503, 'FEATURE_UNAVAILABLE', '관련 링크 기능이 비활성 상태입니다.')
        try:
            items = read_catalog(settings)['resource_links']
            return Page[ResourceLink](items=items[offset:offset + limit], total=len(items),
                                      limit=limit, offset=offset)
        except CatalogUnavailable:
            return query_error(503, 'FEATURE_UNAVAILABLE', '자료를 조회할 수 없습니다.')

    return router
