"""Real reviewed batch through the backend adapters and v2 engine, no fake responses."""
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from backend.importer import import_directory
from backend.main import invalid
from backend.opportunity_query import create_opportunity_router
from backend.service_adapters import create_service_router
from backend.settings import Settings
from shared.models import RecommendationApiResponse


@pytest.fixture
def real_flow(tmp_path):
    db = tmp_path / 'real.db'
    import_directory('data/normalized', db, mode='real')
    settings = Settings(_env_file=None, database_url='sqlite:///' + str(db), data_mode='real')
    time = [datetime.fromisoformat('2026-11-13T00:00:00+09:00')]
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, invalid)
    app.include_router(create_opportunity_router(settings, enabled=lambda: True))
    app.include_router(create_service_router(settings, enabled=lambda name: name == 'recommendations',
                                             clock=lambda: time[0]))
    with TestClient(app) as client:
        yield client, db, settings, time


def test_positive_real_http_preserves_originals_and_explains_unknown(real_flow):
    client, db, _, _ = real_flow
    before = db.read_bytes()
    response = client.post('/api/v1/recommendations', json={'profile': {'interests': ['사업']}})
    assert response.status_code == 200
    result = RecommendationApiResponse.model_validate(response.json())
    assert result.candidate_count == 2
    assert [x.opportunity.id for x in result.items] == ['dankook-recruitment-186367', 'dankook-recruitment-186370']
    for item in result.items:
        assert item.recommendation.relevance_score == 40
        assert item.recommendation.eligibility == 'unknown'
        assert item.opportunity.source_kind == 'real'
        assert item.opportunity.unresolved_conditions
        original = client.get('/api/v1/opportunities/' + item.opportunity.id)
        assert original.status_code == 200
        assert original.json() == item.opportunity.model_dump(mode='json')
        assert item.recommendation.reasons[0].evidence_ids == ['duties']
    assert '마감일이 기재되지 않은' in ' '.join(result.items[1].recommendation.cautions)
    assert db.read_bytes() == before


@pytest.mark.parametrize('profile', [{'interests': ['개발']}, {'goal': '사업은 원하지 않음'}])
def test_real_http_empty_results_are_success(real_flow, profile):
    client, _, _, _ = real_flow
    response = client.post('/api/v1/recommendations', json={'profile': profile})
    assert response.status_code == 200
    assert response.json()['items'] == []
    assert response.json()['candidate_count'] == 0


def test_real_http_limit_type_and_deadline(real_flow):
    client, _, _, clock = real_flow
    body = {'profile': {'preferred_job_fields': ['경영·사업']}, 'limit': 1}
    response = client.post('/api/v1/recommendations', json=body).json()
    assert len(response['items']) == 1 and response['candidate_count'] == 2
    assert response['items'][0]['opportunity']['id'] == 'dankook-recruitment-186367'
    assert client.post('/api/v1/recommendations', json={**body, 'types': ['certification']}).json()['items'] == []
    clock[0] = datetime.fromisoformat('2026-11-18T23:59:00+09:00')
    response = client.post('/api/v1/recommendations', json=body).json()
    assert response['candidate_count'] == 1
    assert response['items'][0]['opportunity']['id'] == 'dankook-recruitment-186370'


def test_real_http_invalid_input_and_missing_db_recovery(real_flow):
    client, db, settings, _ = real_flow
    response = client.post('/api/v1/recommendations', json={'profile': {'age': 'private-sentinel'}})
    assert response.status_code == 422
    assert 'private-sentinel' not in response.text
    original_url = settings.database_url
    missing = db.parent / 'missing.db'
    settings.database_url = 'sqlite:///' + str(missing)
    body = {'profile': {'interests': ['사업']}}
    response = client.post('/api/v1/recommendations', json=body)
    assert response.status_code == 503
    assert str(missing) not in response.text
    assert not missing.exists()
    settings.database_url = original_url
    response = client.post('/api/v1/recommendations', json=body)
    assert response.status_code == 200 and len(response.json()['items']) == 2
