import json
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.importer import import_directory
from backend.main import invalid
from backend.opportunity_query import create_opportunity_router
from backend.settings import Settings
from scripts.validate_examples import validate_examples


def make_client(db, mode='demo'):
    settings = Settings(_env_file=None, database_url='sqlite:///' + str(db), data_mode=mode)
    app = FastAPI()
    from fastapi.exceptions import RequestValidationError
    app.add_exception_handler(RequestValidationError, invalid)
    app.include_router(create_opportunity_router(settings))
    return TestClient(app)


@pytest.fixture
def catalog(tmp_path):
    db = tmp_path / '공고 1.db'
    import_directory('contracts/examples', db, mode='demo')
    return db


def test_list_pages_and_original_detail(catalog):
    client = make_client(catalog)
    before = catalog.read_bytes()
    originals = sorted(validate_examples()['opportunities'], key=lambda item: item.id)
    response = client.get('/api/v1/opportunities?limit=2&offset=1')
    assert response.status_code == 200
    assert response.json() == {
        'items': [item.model_dump(mode='json') for item in originals[1:3]],
        'total': 3, 'limit': 2, 'offset': 1}
    for item in originals:
        response = client.get('/api/v1/opportunities/' + item.id)
        assert response.status_code == 200
        assert response.json() == item.model_dump(mode='json')
    beyond = client.get('/api/v1/opportunities?offset=100').json()
    assert beyond['items'] == [] and beyond['total'] == 3
    assert catalog.read_bytes() == before


def test_missing_id(catalog):
    response = make_client(catalog).get('/api/v1/opportunities/not-present')
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'NOT_FOUND'


@pytest.mark.parametrize('query', ['limit=0', 'limit=101', 'offset=-1', 'limit=text'])
def test_bad_pagination(catalog, query):
    response = make_client(catalog).get('/api/v1/opportunities?' + query)
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


def test_empty_imported_database(tmp_path):
    batch = tmp_path / 'empty'
    batch.mkdir()
    for name in ['sources', 'opportunities', 'roles', 'resource_links']:
        (batch / (name + '.json')).write_text('[]', encoding='utf-8')
    db = tmp_path / 'empty.db'
    import_directory(batch, db, mode='demo')
    client = make_client(db)
    assert client.get('/api/v1/opportunities').json() == {
        'items': [], 'total': 0, 'limit': 20, 'offset': 0}
    assert client.get('/api/v1/opportunities/absent').status_code == 404


def test_absent_database_is_not_created(tmp_path):
    db = tmp_path / 'missing-directory' / 'missing.db'
    response = make_client(db).get('/api/v1/opportunities')
    assert response.status_code == 503
    assert not db.parent.exists()
    assert str(db) not in response.text


@pytest.mark.parametrize('damage', ['version', 'payload', 'mode', 'links', 'schema'])
def test_bad_database_is_not_exposed_or_modified(catalog, damage):
    with sqlite3.connect(catalog) as db:
        if damage == 'version':
            db.execute('PRAGMA user_version=99')
        elif damage == 'payload':
            db.execute("UPDATE opportunities SET payload=? WHERE id='synthetic-job'",
                       (json.dumps({'secret': 'private-test-value'}),))
        elif damage == 'mode':
            db.execute("UPDATE opportunities SET source_kind='real'")
        elif damage == 'links':
            db.execute("DELETE FROM opportunities_sources WHERE item_id='synthetic-job'")
        else:
            db.execute('DROP TABLE roles_sources')
    before = catalog.read_bytes()
    response = make_client(catalog).get('/api/v1/opportunities')
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'FEATURE_UNAVAILABLE'
    assert 'private-test-value' not in response.text
    assert catalog.read_bytes() == before


def test_real_mode_cannot_read_demo(catalog):
    assert make_client(catalog, mode='real').get('/api/v1/opportunities').status_code == 503


def test_database_lock_is_safe(catalog):
    with sqlite3.connect(catalog) as lock:
        lock.execute('BEGIN EXCLUSIVE')
        try:
            assert make_client(catalog).get('/api/v1/opportunities').status_code == 503
        finally:
            lock.rollback()



def test_normalized_real_batch_round_trip(tmp_path):
    from pathlib import Path
    from pydantic import TypeAdapter
    from shared.models import Opportunity
    db = tmp_path / 'real.db'
    result = import_directory('data/normalized', db, mode='real')
    assert result['counts']['opportunities']['inserted'] == 3
    expected = TypeAdapter(list[Opportunity]).validate_json(
        Path('data/normalized/opportunities.json').read_text(encoding='utf-8'))
    client = make_client(db, mode='real')
    before = db.read_bytes()
    response = client.get('/api/v1/opportunities')
    assert response.status_code == 200
    assert response.json()['total'] == 3
    assert response.json()['items'] == [item.model_dump(mode='json')
                                      for item in sorted(expected, key=lambda item: item.id)]
    for item in expected:
        response = client.get('/api/v1/opportunities/' + item.id)
        assert response.status_code == 200
        assert response.json() == item.model_dump(mode='json')
    assert db.read_bytes() == before
