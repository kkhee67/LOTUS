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


@pytest.mark.parametrize('field', ['opens_on', 'closes_on', 'exam_on', 'starts_on', 'ends_on', 'published_on'])
@pytest.mark.parametrize('value', ['2026-11-11T00:00:00+09:00', '2026-11-11T00:00:00Z', '2026-11-11 00:00:00', 0, '0'])
def test_date_fields_reject_time_and_epoch_before_coercion(field, value):
    import json
    from pydantic import create_model
    from shared.models import ApplicationInfo, ExamSession, EventSchedule, Opportunity
    owner = next(model for model in (ApplicationInfo, ExamSession, EventSchedule, Opportunity) if field in model.model_fields)
    # Use the real field definition, including its validators, in both input paths.
    probe = create_model('DateFieldProbe', **{field: (owner.model_fields[field].annotation, owner.model_fields[field])})
    with pytest.raises(ValidationError):
        probe.model_validate({field: value})
    with pytest.raises(ValidationError):
        probe.model_validate_json(json.dumps({field: value}))


def test_python_datetime_is_not_silently_truncated_and_dates_round_trip():
    from datetime import date
    for value in (datetime(2026, 11, 11), NOW):
        with pytest.raises(ValidationError):
            ApplicationInfo(closes_on=value)
    for value in ('2026-11-11', date(2026, 11, 11), None):
        application = ApplicationInfo(closes_on=value)
        assert ApplicationInfo.model_validate_json(application.model_dump_json()) == application
    with pytest.raises(ValidationError):
        ApplicationInfo(closes_on='2026-02-30')


def test_midnight_deadline_keeps_exact_time_and_date_only_stays_inclusive():
    with pytest.raises(ValidationError):
        ApplicationInfo.model_validate_json('{"status":"open","closes_on":"2026-11-11T00:00:00+09:00"}')
    exact = ApplicationInfo.model_validate_json('{"status":"open","closes_at":"2026-11-11T00:00:00+09:00"}')
    midnight = datetime.fromisoformat('2026-11-11T00:00:00+09:00')
    assert application_state(exact, now=midnight).status == 'closed'
    assert application_state(exact, now=NOW).status == 'closed'
    date_only = ApplicationInfo(status='open', closes_on='2026-11-11')
    assert application_state(date_only, now=NOW).status == 'open'
