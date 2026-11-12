from datetime import datetime
from shared.models import RoleAdviceRequest, RoleAdviceResponse, Opportunity, RoleProfile
from recommender.errors import FeatureUnavailableError

def suggest_roles(request: RoleAdviceRequest, roles: list[RoleProfile], *, now: datetime) -> RoleAdviceResponse:
    raise FeatureUnavailableError("suggest_roles is not implemented")
