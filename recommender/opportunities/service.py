from datetime import datetime
from shared.models import RecommendationRequest, RecommendationResponse, Opportunity, RoleProfile
from recommender.errors import FeatureUnavailableError

def recommend(request: RecommendationRequest, opportunities: list[Opportunity], *, now: datetime) -> RecommendationResponse:
    raise FeatureUnavailableError("recommend is not implemented")
