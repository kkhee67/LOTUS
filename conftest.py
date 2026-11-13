"""Shared, opt-in fixtures for backend and integration regressions."""
import pytest
from backend.importer import import_directory
from backend.settings import Settings
from tests.support import REAL_BATCH, RECOMMENDATION_TIME, datetime_at


@pytest.fixture
def real_catalog(tmp_path):
    db = tmp_path / 'real.db'
    import_directory(REAL_BATCH, db, mode='real')
    settings = Settings(_env_file=None, database_url='sqlite:///' + str(db), data_mode='real')
    return db, settings


@pytest.fixture
def recommendation_clock(monkeypatch):
    from backend import service_adapters
    clock = [RECOMMENDATION_TIME]
    monkeypatch.setattr(service_adapters, 'datetime', datetime_at(clock))
    return clock
