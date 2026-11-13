"""Regressions for the checked-in public batch, not live source availability."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.importer import import_directory
from backend.opportunity_query import read_opportunities
from backend.service_adapters import assemble_recommendations
from shared.models import RecommendationApiResponse, RecommendationRequest
from datetime import datetime


@pytest.fixture
def real_server(tmp_path, monkeypatch):
    db = tmp_path / 'real.db'
    import_directory('data/normalized', db, mode='real')
    monkeypatch.setattr(main.settings, 'database_url', 'sqlite:///' + str(db))
    monkeypatch.setattr(main.settings, 'data_mode', 'real')
    return TestClient(main.app), db


@pytest.mark.parametrize('interest', ['business', '경영·사업', '경영', '사업'])
def test_actual_business_recommendation_preserves_original_and_evidence(real_server, interest):
    client, db = real_server
    before = db.read_bytes()
    response = client.post('/api/v1/recommendations', json={
        'profile': {'interests': [interest]}, 'types': ['job'], 'limit': 1})
    assert response.status_code == 200
    result = RecommendationApiResponse.model_validate(response.json())
    assert len(result.items) == result.candidate_count == 1 and result.engine == 'rules'
    item = result.items[0]
    assert item.opportunity.id == 'dankook-recruitment-186370'
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
    # Pin the dataset verification date for reproducibility; no clock or network mocks.
    result = assemble_recommendations(
        RecommendationRequest(profile={'interests': ['경영·사업']}), read_opportunities(main.settings),
        now=datetime.fromisoformat('2026-11-13T12:00:00+09:00'))
    assert [item.opportunity.id for item in result.items] == ['dankook-recruitment-186370']
