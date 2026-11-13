"""Shared reviewed batch and deterministic time for regression tests."""
from datetime import datetime
from pathlib import Path

REAL_BATCH = Path(__file__).resolve().parents[1] / 'data/normalized'
RECOMMENDATION_TIME = datetime.fromisoformat('2026-11-13T12:00:00+09:00')


def datetime_at(clock):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                raise ValueError('Test server requires timezone-aware time')
            return clock[0].astimezone(tz)
    return FixedDatetime
