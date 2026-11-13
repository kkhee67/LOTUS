"""Offline integration against the reviewed, committed real batch at fixed times."""
from datetime import datetime
import sqlite3

from backend.importer import import_directory
from data_pipeline.normalize import ROOT, read_dataset
from shared.models import Opportunity, RecommendationApiItem, RecommendationApiResponse, RecommendationRequest
from recommender.opportunities.service import recommend

from tests.support import RECOMMENDATION_TIME as NOW


def test_real_batch_round_trip_recommendation_and_api_contract(tmp_path):
    directory = ROOT / 'data/normalized'
    original = read_dataset(directory)['opportunities']
    before = [item.model_dump_json() for item in original]
    db = tmp_path / 'real.db'
    import_directory(directory, db, mode='real')
    with sqlite3.connect(db) as connection:
        restored = [Opportunity.model_validate_json(row[0]) for row in
                    connection.execute('SELECT payload FROM opportunities ORDER BY id')]
    req = RecommendationRequest(profile={'interests': ['사업']})
    result = recommend(req, restored, now=NOW)
    assert result == recommend(req, original, now=NOW)
    assert [(x.opportunity_id, x.relevance_score, x.eligibility) for x in result.items] == [
        ('dankook-recruitment-186367', 40, 'unknown'),
        ('dankook-recruitment-186370', 40, 'unknown')]
    assert result.candidate_count == 2
    assert result.warnings == []
    by_id = {x.id: x for x in restored}
    response = RecommendationApiResponse(items=[RecommendationApiItem(
        opportunity=by_id[x.opportunity_id], recommendation=x) for x in result.items],
        candidate_count=result.candidate_count, engine=result.engine, warnings=result.warnings)
    assert RecommendationApiResponse.model_validate_json(response.model_dump_json()) == response
    for item in response.items:
        assert item.opportunity.unresolved_conditions
        assert item.recommendation.reasons[0].evidence_ids == ['duties']
        undated = item.opportunity.application.closes_at is None
        cautions = ' '.join(item.recommendation.cautions)
        assert ('마감일이 기재되지 않은' in cautions) == undated
        if undated:
            assert item.opportunity.checked_at.isoformat() in cautions
    assert before == [item.model_dump_json() for item in original]
    assert not recommend(RecommendationRequest(profile={'interests': ['개발']}), original, now=NOW).items


def test_real_batch_exact_deadline_and_negative_goal():
    items = read_dataset(ROOT / 'data/normalized')['opportunities']
    request = RecommendationRequest(profile={'interests': ['사업']})
    before = recommend(request, items, now=datetime.fromisoformat('2026-11-18T23:58:59+09:00'))
    after = recommend(request, items, now=datetime.fromisoformat('2026-11-18T23:59:00+09:00'))
    assert before.candidate_count == 2
    assert [x.opportunity_id for x in after.items] == ['dankook-recruitment-186370']
    assert not recommend(RecommendationRequest(profile={'goal': '사업은 원하지 않음'}), items, now=NOW).items
