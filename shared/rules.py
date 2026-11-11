from datetime import datetime
from zoneinfo import ZoneInfo
from shared.models import ApplicationInfo, StrictModel
from typing import Literal

CONTRACT_VERSION = '4.1-draft'
DEFAULT_TIMEZONE = 'Asia/Seoul'
SEOUL = ZoneInfo(DEFAULT_TIMEZONE)

class ApplicationState(StrictModel):
    status: Literal['open', 'upcoming', 'closed', 'unknown']
    cautions: list[str]

def application_state(application: ApplicationInfo, *, now: datetime) -> ApplicationState:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('now must include a timezone')
    today = now.astimezone(SEOUL).date()
    cautions = []
    if application.status == 'closed':
        return ApplicationState(status='closed', cautions=[])
    if (application.closes_at and now >= application.closes_at) or (application.closes_on and today > application.closes_on):
        return ApplicationState(status='closed', cautions=[])
    if application.closes_on == today:
        cautions.append('마감일 당일입니다. 정확한 마감 시각을 원문에서 확인하세요.')
    if (application.opens_at and now < application.opens_at) or (application.opens_on and today < application.opens_on):
        return ApplicationState(status='upcoming', cautions=cautions)
    status = application.status
    if status == 'upcoming' and (application.opens_at or application.opens_on):
        status = 'open'
    return ApplicationState(status=status, cautions=cautions)
