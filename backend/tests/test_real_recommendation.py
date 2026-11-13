"""Regressions for the checked-in public batch, not live source availability."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.opportunity_query import read_opportunities
from backend.service_adapters import assemble_recommendations
from shared.models import RecommendationApiResponse, RecommendationRequest
from datetime import datetime
from tests.support import RECOMMENDATION_TIME


@pytest.fixture
def real_server(real_catalog, recommendation_clock, monkeypatch):
    db, settings = real_catalog
    monkeypatch.setattr(main.settings, 'database_url', settings.database_url)
    monkeypatch.setattr(main.settings, 'data_mode', settings.data_mode)
    clock = recommendation_clock
    with TestClient(main.app) as client:
        yield client, db, clock


@pytest.mark.parametrize('interest', ['business', '경영·사업', '경영', '사업'])
def test_actual_business_recommendation_preserves_original_and_evidence(real_server, interest):
    client, db, _ = real_server
    before = db.read_bytes()
    response = client.post('/api/v1/recommendations', json={
        'profile': {'interests': [interest]}, 'types': ['job'], 'limit': 1})
    assert response.status_code == 200
    result = RecommendationApiResponse.model_validate(response.json())
    assert len(result.items) == 1 and result.candidate_count == 2
    assert result.engine == 'rules'
    item = result.items[0]
    assert item.opportunity.id == 'dankook-recruitment-186367'
    assert item.opportunity.source_kind == 'real'
    original = next(row for row in json.loads(Path('data/normalized/opportunities.json').read_text(encoding='utf-8'))
                    if row['id'] == item.opportunity.id)
    # Compare with the common model's representation, including default fields.
    from shared.models import Opportunity
    assert item.opportunity == Opportunity.model_validate(original)
    assert client.get('/api/v1/opportunities/' + item.opportunity.id).json() == item.opportunity.model_dump(mode='json')
    assert item.recommendation.relevance_score == 40
    assert item.recommendation.eligibility == 'unknown'
    assert item.recommendation.reasons[0].evidence_ids == ['duties']
    assert any('확인' in caution for caution in item.recommendation.cautions)
    assert db.read_bytes() == before


@pytest.mark.parametrize('interest', ['소프트웨어', '디자인', '데이터'])
def test_unrelated_real_batch_stays_empty(real_server, interest):
    response = real_server[0].post('/api/v1/recommendations', json={'profile': {'interests': [interest]}})
    assert response.status_code == 200
    assert response.json()['items'] == [] and response.json()['candidate_count'] == 0


def test_batch_replay_with_explicit_aware_time(real_server):
    # Replay at the same aware instant independently of the wall clock.
    result = assemble_recommendations(
        RecommendationRequest(profile={'interests': ['경영·사업']}), read_opportunities(main.settings),
        now=RECOMMENDATION_TIME)
    assert result.candidate_count == 2
    assert [item.opportunity.id for item in result.items] == [
        'dankook-recruitment-186367', 'dankook-recruitment-186370']


@pytest.mark.parametrize('instant,expected', [
    ('2026-11-18T23:58:59+09:00', ['dankook-recruitment-186367', 'dankook-recruitment-186370']),
    ('2026-11-18T23:59:00+09:00', ['dankook-recruitment-186370']),
    ('2026-11-18T23:59:01+09:00', ['dankook-recruitment-186370']),
])
def test_real_main_http_deadline_preserves_remaining_candidate(real_server, instant, expected):
    client, db, clock = real_server
    before = db.read_bytes()
    clock[0] = datetime.fromisoformat(instant)
    response = client.post('/api/v1/recommendations', json={'profile': {'interests': ['사업']}})
    assert response.status_code == 200
    result = RecommendationApiResponse.model_validate(response.json())
    assert result.candidate_count == len(expected)
    assert [item.opportunity.id for item in result.items] == expected
    assert all(item.recommendation.relevance_score == 40 for item in result.items)
    assert all(item.recommendation.eligibility == 'unknown' for item in result.items)
    assert db.read_bytes() == before
