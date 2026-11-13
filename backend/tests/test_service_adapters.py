import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from backend import main
from backend.importer import import_directory
from backend.service_adapters import create_service_router
from backend.settings import Settings
from recommender.errors import FeatureUnavailableError
from recommender.opportunities import service as engine
from shared.models import Capability

NOW = datetime.fromisoformat('2026-11-11T12:00:00+09:00')
BODY = {'profile': {'interests': ['소프트웨어'], 'goal': 'private-profile-sentinel'}, 'limit': 1}


@pytest.fixture
def service(tmp_path):
    db = tmp_path / 'catalog.db'
    import_directory('contracts/examples', db, mode='demo')
    settings = Settings(_env_file=None, database_url='sqlite:///' + str(db), data_mode='demo')
    active = {'recommendations', 'resource-links', 'career-roles', 'activity-plan', 'interview-guide'}
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, main.invalid)
    app.include_router(create_service_router(settings, enabled=lambda name: name in active, clock=lambda: NOW))
    return TestClient(app), db, active, settings


def test_real_engine_http_combines_original_without_db_changes(service):
    client, db, _, _ = service
    before = db.read_bytes()
    response = client.post('/api/v1/recommendations', json=BODY)
    assert response.status_code == 200
    data = response.json()
    assert len(data['items']) == 1 and data['candidate_count'] >= 1 and data['engine'] == 'rules'
    with sqlite3.connect(db) as connection:
        originals = dict(connection.execute('SELECT id, payload FROM opportunities'))
    for item in data['items']:
        assert item['opportunity'] == json.loads(originals[item['recommendation']['opportunity_id']])
    assert db.read_bytes() == before


def test_real_batch_can_legitimately_return_zero(service):
    client, db, _, settings = service
    real = db.parent / 'real.db'
    import_directory('data/normalized', real, mode='real')
    settings.database_url = 'sqlite:///' + str(real)
    settings.data_mode = 'real'
    before = real.read_bytes()
    response = client.post('/api/v1/recommendations', json=BODY)
    assert response.status_code == 200
    assert response.json() == {'items': [], 'candidate_count': 0, 'engine': 'rules', 'warnings': []}
    assert real.read_bytes() == before


@pytest.mark.parametrize('name', ['recommendations', 'career-roles', 'activity-plan', 'interview-guide', 'resource-links'])
def test_off_prevents_db_and_engine_access(service, monkeypatch, name):
    client, _, active, _ = service
    active.remove(name)
    def forbidden(*args, **kwargs):
        raise AssertionError('disabled feature accessed storage')
    monkeypatch.setattr('backend.service_adapters.read_catalog', forbidden)
    response = (client.get('/api/v1/resource-links') if name == 'resource-links'
                else client.post('/api/v1/' + name, json={'profile': {'goal': 'test'}}))
    assert response.status_code == 503


@pytest.mark.parametrize('damage', ['missing', 'mode', 'payload', 'locked'])
def test_catalog_errors_safe_and_read_only(service, damage):
    client, db, _, settings = service
    lock = None
    if damage == 'missing':
        settings.database_url = 'sqlite:///' + str(db.parent / 'secret-missing.db')
    elif damage == 'mode':
        settings.data_mode = 'real'
    elif damage == 'payload':
        with sqlite3.connect(db) as connection:
            connection.execute("UPDATE opportunities SET payload=?", ('{"secret":"private-db-sentinel"}',))
    else:
        lock = sqlite3.connect(db)
        lock.execute('BEGIN EXCLUSIVE')
    before = db.read_bytes()
    try:
        response = client.post('/api/v1/recommendations', json=BODY)
        assert response.status_code == 503
        assert 'private-' not in response.text and 'secret-' not in response.text and str(db) not in response.text
        assert db.read_bytes() == before
    finally:
        if lock:
            lock.rollback()
            lock.close()


@pytest.mark.parametrize('damage', ['id', 'evidence', 'type', 'count', 'limit', 'order', 'duplicate', 'ineligible', 'llm', 'exception'])
def test_untrusted_engine_response_rejected_without_leak(service, monkeypatch, damage):
    client, _, _, _ = service
    real = engine.recommend
    def corrupt(request, opportunities, *, now):
        if damage == 'exception':
            raise RuntimeError('private-profile-sentinel private-token-sentinel')
        request.limit = 20
        result = real(request, opportunities, now=now).model_dump()
        item = result['items'][0]
        if damage == 'id': item['opportunity_id'] = 'missing'
        elif damage == 'evidence': item['reasons'][0]['evidence_ids'] = ['missing']
        elif damage == 'type': item['opportunity_id'] = 'synthetic-certification'
        elif damage == 'count': result['candidate_count'] = 10000
        elif damage == 'limit': result['items'] = result['items'] * 2
        elif damage == 'order':
            item['relevance_score'] = 1
            other = dict(item, opportunity_id='synthetic-other', relevance_score=99)
            result['items'] = [item, other]; result['candidate_count'] = 2
        elif damage == 'duplicate': result['items'] = [item, item]
        elif damage == 'ineligible': item['eligibility'] = 'ineligible'
        elif damage == 'llm':
            item['explanation_source'] = 'llm'; result['engine'] = 'rules+llm'
        return result
    monkeypatch.setattr(engine, 'recommend', corrupt)
    response = client.post('/api/v1/recommendations', json={**BODY, 'types': ['job']})
    assert response.status_code == 500
    assert response.json()['error']['code'] == 'INTERNAL_ERROR'
    assert 'private-' not in response.text and 'missing' not in response.text


def test_engine_cannot_rewrite_db_original(service, monkeypatch):
    client, _, _, _ = service
    real = engine.recommend
    def mutate(request, opportunities, *, now):
        result = real(request, opportunities, now=now)
        for item in opportunities:
            item.title = 'engine altered title'
        return result
    monkeypatch.setattr(engine, 'recommend', mutate)
    response = client.post('/api/v1/recommendations', json=BODY)
    assert response.status_code == 200
    assert all(item['opportunity']['title'] != 'engine altered title' for item in response.json()['items'])


def test_resource_links_actual_rows_and_pages(service):
    client, db, _, _ = service
    before = db.read_bytes()
    original = json.loads(Path('contracts/examples/resource_links.json').read_text(encoding='utf-8'))
    result = client.get('/api/v1/resource-links?limit=1').json()
    assert result['total'] == len(original) and result['items'] == sorted(original, key=lambda item: item['id'])[:1]
    assert client.get('/api/v1/resource-links?offset=100').json()['items'] == []
    assert client.get('/api/v1/resource-links?limit=0').status_code == 422
    assert db.read_bytes() == before


@pytest.mark.parametrize('name', ['career-roles', 'activity-plan', 'interview-guide'])
def test_actual_unimplemented_engines_remain_unavailable(service, name):
    client, _, _, _ = service
    response = client.post('/api/v1/' + name, json={'profile': {'goal': 'test'}})
    assert response.status_code == 503


@pytest.mark.parametrize('name, module, fn, payload', [
    ('career-roles', 'role_engine', 'suggest_roles', {'items': [{'role_id': 'missing', 'explanation': 'test', 'source_ids': ['missing']}]}),
    ('activity-plan', 'roadmap_engine', 'make_plan', {'steps': [{'title': 'test', 'description': 'test', 'kind': 'opportunity', 'opportunity_id': 'missing'}]}),
    ('interview-guide', 'interview_engine', 'make_interview_guide', {'questions': [{'question': 'test', 'preparation_tip': 'test', 'experience_ids': ['missing']}]}),
])
def test_future_engine_invalid_references_rejected(service, monkeypatch, name, module, fn, payload):
    client, _, _, _ = service
    monkeypatch.setattr(f'backend.service_adapters.{module}.{fn}', lambda *args, **kwargs: payload)
    response = client.post('/api/v1/' + name, json={'profile': {'goal': 'test'}})
    assert response.status_code == 500 and 'missing' not in response.text


@pytest.mark.parametrize('name', ['activity-plan', 'interview-guide'])
def test_missing_input_context_is_404(service, name):
    response = service[0].post('/api/v1/' + name, json={'profile': {'goal': 'test'}, 'role_ids': ['missing']})
    assert response.status_code == 404


def test_engine_failure_does_not_break_catalog(service, monkeypatch):
    client, db, _, _ = service
    monkeypatch.setattr(engine, 'recommend', lambda *args, **kwargs: (_ for _ in ()).throw(FeatureUnavailableError('private-token')))
    assert client.post('/api/v1/recommendations', json=BODY).status_code == 503
    assert client.get('/api/v1/resource-links').status_code == 200
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT count(*) FROM opportunities').fetchone()[0] == 3


def test_main_adapter_can_be_enabled_for_test_only(service, monkeypatch):
    _, db, _, _ = service
    monkeypatch.setattr(main.settings, 'database_url', 'sqlite:///' + str(db))
    monkeypatch.setattr(main.settings, 'data_mode', 'demo')
    monkeypatch.setitem(main.capability_flags, 'recommendations', Capability(enabled=True, implemented=True))
    main.validate_capability_flags(main.capability_flags)
    client = TestClient(main.app)
    # Future synthetic contract data relative to real clock can produce no results; still valid HTTP.
    assert client.post('/api/v1/recommendations', json=BODY).status_code == 200
    assert client.get('/api/v1/opportunities').status_code == 200
    assert client.post('/api/v1/activity-plan', json={'profile': {'goal': 'test'}}).status_code == 503


@pytest.mark.parametrize('application,expected,caution', [
    ({'status': 'closed'}, 0, None),
    ({'status': 'unknown'}, 0, None),
    ({'status': 'open', 'closes_at': '2026-11-11T12:00:00+09:00'}, 0, None),
    ({'status': 'open', 'closes_at': '2026-11-11T12:00:01+09:00'}, 1, '확인'),
    ({'status': 'open', 'closes_on': '2026-11-10'}, 0, None),
    ({'status': 'open', 'closes_on': '2026-11-11'}, 1, '마감일 당일'),
])
def test_http_deadline_and_unknown_eligibility(service, tmp_path, application, expected, caution):
    client, db, _, _ = service
    batch = tmp_path / 'boundaries'
    batch.mkdir()
    for name in ['sources', 'roles', 'resource_links']:
        (batch / f'{name}.json').write_bytes(Path(f'contracts/examples/{name}.json').read_bytes())
    item = json.loads(Path('contracts/examples/opportunities.json').read_text(encoding='utf-8'))[0]
    item['application'] = application
    (batch / 'opportunities.json').write_text(json.dumps([item]), encoding='utf-8')
    # Other existing rows remain by design, so explicitly limit to job type.
    import_directory(batch, db, mode='demo')
    response = client.post('/api/v1/recommendations', json={**BODY, 'types': ['job']})
    assert response.status_code == 200
    assert len(response.json()['items']) == expected
    if expected:
        recommendation = response.json()['items'][0]['recommendation']
        assert recommendation['eligibility'] == 'unknown'
        assert any(caution in text for text in recommendation['cautions'])


@pytest.mark.parametrize('reverse', [False, True])
def test_adapter_checks_tie_sort_and_candidate_count(service, monkeypatch, reverse):
    from backend.service_adapters import assemble_recommendations
    from scripts.validate_examples import validate_examples
    from shared.models import RecommendationRequest
    original = validate_examples()['opportunities'][0]
    opportunities = [original.model_copy(update={'id': key}, deep=True) for key in ['a', 'b', 'c']]
    def supplied(*args, **kwargs):
        rows = [dict(opportunity_id=key, relevance_score=40, eligibility=status,
                     reasons=[{'text': 'test', 'evidence_ids': [original.evidence[0].id]}],
                     explanation_source='template') for key, status in [('b', 'eligible'), ('a', 'unknown')]]
        return {'items': list(reversed(rows)) if reverse else rows, 'candidate_count': 3, 'engine': 'rules'}
    monkeypatch.setattr(engine, 'recommend', supplied)
    request = RecommendationRequest(profile={'goal': 'test'}, limit=2)
    if reverse:
        with pytest.raises(ValueError, match='order'):
            assemble_recommendations(request, opportunities, now=NOW)
    else:
        result = assemble_recommendations(request, opportunities, now=NOW)
        assert [item.opportunity.id for item in result.items] == ['b', 'a']
        assert result.candidate_count == 3


def test_empty_initialized_db_returns_empty_recommendations(service, tmp_path):
    client, _, _, settings = service
    batch = tmp_path / 'empty'
    batch.mkdir()
    for name in ['sources', 'opportunities', 'roles', 'resource_links']:
        (batch / f'{name}.json').write_text('[]', encoding='utf-8')
    db = tmp_path / 'empty.db'
    import_directory(batch, db, mode='demo')
    settings.database_url = 'sqlite:///' + str(db)
    response = client.post('/api/v1/recommendations', json=BODY)
    assert response.status_code == 200
    assert response.json() == {'items': [], 'candidate_count': 0, 'engine': 'rules', 'warnings': []}
