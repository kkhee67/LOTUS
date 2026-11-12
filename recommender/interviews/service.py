from datetime import datetime
from shared.models import InterviewGuideRequest, InterviewGuideResponse, Opportunity, RoleProfile
from recommender.errors import FeatureUnavailableError

def make_interview_guide(request: InterviewGuideRequest, roles: list[RoleProfile], opportunities: list[Opportunity], *, now: datetime) -> InterviewGuideResponse:
    raise FeatureUnavailableError("make_interview_guide is not implemented")
