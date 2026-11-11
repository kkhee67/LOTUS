from datetime import datetime
from shared.models import ActivityPlanRequest, ActivityPlanResponse, Opportunity, RoleProfile
from recommender.errors import FeatureUnavailableError

def make_plan(request: ActivityPlanRequest, roles: list[RoleProfile], opportunities: list[Opportunity], *, now: datetime) -> ActivityPlanResponse:
    raise FeatureUnavailableError("make_plan is not implemented")
