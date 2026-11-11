from datetime import datetime

import pytest
from pydantic import ValidationError

from shared.models import ApplicationInfo
from shared.rules import application_state

NOW = datetime.fromisoformat('2026-11-11T12:00:00+09:00')


@pytest.mark.parametrize('boundary', [
    {'opens_on': '2026-11-12'},
    {'opens_at': '2026-11-12T09:00:00+09:00'},
    {'opens_on': '2026-11-10'},
])
def test_unknown_status_stays_unknown_until_confirmed_closed(boundary):
    application = ApplicationInfo(status='unknown', **boundary)
    before = application.model_dump()
    assert application_state(application, now=NOW).status == 'unknown'
    assert application.model_dump() == before


def test_unknown_deadline_day_keeps_caution_and_closes_at_exact_boundary():
    application = ApplicationInfo(status='unknown', closes_on='2026-11-11')
    result = application_state(application, now=NOW)
    assert result.status == 'unknown' and result.cautions
    assert application_state(application, now=datetime.fromisoformat('2026-11-12T00:00:00+09:00')).status == 'closed'
    assert application_state(ApplicationInfo(status='unknown', closes_at=NOW), now=NOW).status == 'closed'


@pytest.mark.parametrize('close', [
    '2026-11-12T00:00:00+09:00',
    '2026-11-11T15:00:00+00:00',
    '2026-11-11T23:59:59+09:00',
])
def test_date_opening_requires_a_later_exact_closing(close):
    with pytest.raises(ValidationError):
        ApplicationInfo(status='upcoming', opens_on='2026-11-12', closes_at=close)


@pytest.mark.parametrize('boundaries', [
    {'opens_on': '2026-11-12', 'closes_at': '2026-11-12T00:00:00.000001+09:00'},
    {'opens_on': '2026-11-12', 'closes_at': '2026-11-11T16:00:00+00:00'},
    {'opens_on': '2026-11-12', 'closes_on': '2026-11-12'},
    {'opens_at': '2026-11-12T23:59:59+09:00', 'closes_on': '2026-11-12'},
    {'opens_on': '9999-12-31', 'closes_on': '9999-12-31'},
])
def test_valid_mixed_precision_and_date_only_windows_remain_supported(boundaries):
    assert ApplicationInfo(**boundaries)
