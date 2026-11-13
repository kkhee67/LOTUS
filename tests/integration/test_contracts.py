import copy
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from backend.main import app
from backend.settings import Settings
from shared.models import (ApplicationInfo, UserProfile, Opportunity, RecommendationApiResponse,
                           RecommendationRequest, RoleAdviceRequest, ActivityPlanRequest,
                           InterviewGuideRequest)
from shared.rules import application_state
from shared.validation import validate_dataset
from scripts.validate_examples import validate_examples, load
from recommender.errors import FeatureUnavailableError
from recommender.opportunities.service import recommend
from recommender.roles.service import suggest_roles
from recommender.roadmap.service import make_plan
from recommender.interviews.service import make_interview_guide

NOW = datetime.fromisoformat('2026-11-11T12:00:00+09:00')
client = TestClient(app)


@pytest.mark.parametrize('profile', [{'major': '개발'}, {'interests': ['디자인']},
                                    {'preferred_job_fields': ['개발']}, {'goal': '준비하기'},
                                    {'major': '개발', 'education_status': 'graduated'}])
def test_minimum_profile(profile):
    parsed = UserProfile.model_validate(profile)
    assert parsed.academic_year is None
    assert parsed.experience_status == 'unknown'


@pytest.mark.parametrize('extra', [{}, {'major': '  '}, {'interests': [' ']},
    {'major': '개발', 'age': True}, {'goal': '준비', 'unexpected': 1},
    {'goal': '준비', 'experience_status': 'provided'},
    {'goal': '준비', 'experience_status': 'none', 'experiences': [{'id':'e','kind':'club','title':'활동'}]}])
def test_invalid_profiles(extra):
    with pytest.raises(ValidationError):
        UserProfile.model_validate(extra)


def test_experience_and_regions():
    none = UserProfile(goal='준비', experience_status='none')
    unknown = UserProfile(goal='준비')
    assert none.experiences == unknown.experiences == []
    assert none.experience_status != unknown.experience_status
    p = UserProfile(goal='준비', residence_region='서울', preferred_job_regions=['부산'],
                    experience_status='provided', experiences=[{'id':'e','kind':'course_project','title':'수업'}])
    assert p.experiences[0].kind == 'course_project'
    assert p.residence_region != p.preferred_job_regions[0]


def test_examples_and_certification_state():
    data = validate_examples()
    cert = data['opportunities'][1]
    assert cert.certification.status == 'active'
    assert application_state(cert.certification.exam_sessions[0].application, now=NOW).status == 'closed'
    assert data['opportunities'][2].certification.exam_sessions == []
    assert data['opportunities'][0].eligibility_rules[0].expression.kind == 'any'
    assert data['opportunities'][0].eligibility_rules[1].expression.kind == 'exception'


def test_dataset_reference_and_mixing_rejected():
    for mutation in ('missing', 'duplicate', 'mixed', 'unknown_field'):
        data = validate_examples()
        if mutation == 'missing':
            data['opportunities'][0].source_ids = ['absent']
        elif mutation == 'duplicate':
            data['sources'].append(data['sources'][0])
        elif mutation == 'mixed':
            data['sources'][0].source_kind = 'real'
        else:
            data['opportunities'][0].fields = ['made-up-code']
        with pytest.raises(ValueError):
            validate_dataset(**data)


@pytest.mark.parametrize('delta,expected', [(-1,'open'),(0,'closed'),(1,'closed')])
def test_exact_deadline(delta, expected):
    app_info = ApplicationInfo(status='open', closes_at=NOW)
    before = app_info.model_dump()
    assert application_state(app_info, now=NOW + timedelta(seconds=delta)).status == expected
    assert app_info.model_dump() == before


def test_date_only_and_timezone():
    info = ApplicationInfo(status='open', closes_on=NOW.date())
    assert application_state(info, now=NOW).cautions
    assert application_state(info, now=datetime.fromisoformat('2026-11-11T14:59:59+00:00')).status == 'open'
    assert application_state(info, now=datetime.fromisoformat('2026-11-11T15:00:00+00:00')).status == 'closed'
    with pytest.raises(ValueError):
        application_state(info, now=datetime(2026,11,11))


def test_opening_and_source_closed_or_unknown():
    info = ApplicationInfo(status='upcoming', opens_at=NOW)
    assert application_state(info, now=NOW-timedelta(seconds=1)).status == 'upcoming'
    assert application_state(info, now=NOW).status == 'open'
    assert application_state(ApplicationInfo(status='closed', closes_on='2027-01-01'), now=NOW).status == 'closed'
    assert application_state(ApplicationInfo(opens_on='2026-01-01'), now=NOW).status == 'unknown'
    assert application_state(ApplicationInfo(status='upcoming'), now=NOW).status == 'upcoming'


@pytest.mark.parametrize('values', [{'closes_at':'2026-11-11T12:00:00'},
    {'opens_on':'2026-11-12','closes_on':'2026-11-11'},
    {'closes_on':'2026-11-11','closes_at':'2026-11-11T12:00:00+09:00'}])
def test_invalid_dates(values):
    with pytest.raises(ValidationError):
        ApplicationInfo(**values)


@pytest.mark.parametrize('mutation', ['id','evidence','score','count','engine'])
def test_bad_recommendation_references(mutation):
    data = load('recommendation_api_response.json')
    item = data['items'][0]['recommendation']
    if mutation == 'id': item['opportunity_id'] = 'missing'
    elif mutation == 'evidence': item['reasons'][0]['evidence_ids'] = ['missing']
    elif mutation == 'score': item['relevance_score'] = 101
    elif mutation == 'count': data['candidate_count'] = 0
    else: data['engine'] = 'rules+llm'
    with pytest.raises(ValidationError):
        RecommendationApiResponse.model_validate(data)


def test_unknown_rule_and_evidence_are_rejected():
    for mutation in ('rule','evidence','experience'):
        data = load('opportunities.json')[0]
        if mutation == 'rule': data['eligibility_rules'][0]['expression'] = {'kind':'eval','code':'1+1'}
        elif mutation == 'evidence': data['eligibility_rules'][0]['evidence_ids'] = ['missing']
        else: data['experience_required'] = False
        with pytest.raises(ValidationError):
            Opportunity.model_validate(data)


@pytest.mark.parametrize('path', ['/opportunities','/opportunities/absent','/resource-links'])
def test_unavailable_catalog_or_unimplemented_links(path):
    response = client.get('/api/v1'+path)
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'FEATURE_UNAVAILABLE'


def test_options_capabilities_openapi_cors():
    assert client.get('/api/v1/options').json() == json.loads(Path('shared/catalog.json').read_text(encoding='utf-8'))
    caps = client.get('/api/v1/capabilities').json()
    assert set(caps) == {'recommendations','career-roles','activity-plan','interview-guide','opportunities','resource-links'}
    assert caps['opportunities']['enabled'] and caps['opportunities']['implemented']
    assert all(x['enabled'] == (name == 'recommendations') and x['implemented'] == (name in {'recommendations', 'resource-links'}) for name, x in caps.items() if name != 'opportunities')
    schema = app.openapi()
    for path in ['recommendations','career-roles','activity-plan','interview-guide']:
        route = schema['paths']['/api/v1/'+path]['post']
        assert 'requestBody' in route and '503' in route['responses'] and '200' in route['responses']
        bad = client.post('/api/v1/'+path,json={'profile':{'goal':'secret-value','extra':'private'}})
        assert bad.status_code == 422 and 'secret-value' not in bad.text and 'private' not in bad.text
    response = client.options('/api/v1/recommendations',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert client.get('/api/v1/opportunities?limit=0').status_code == 422


def test_env_file_and_validation(tmp_path):
    env = tmp_path/'test.env'
    env.write_text('CORS_ORIGINS=http://localhost:5174\nDATA_MODE=real\n',encoding='utf-8')
    settings = Settings(_env_file=env)
    assert settings.allowed_origins == ['http://localhost:5174']
    assert settings.data_mode == 'real'
    with pytest.raises(ValidationError):
        Settings(_env_file=None,cors_origins='http://localhost:5173/api/v1')


@pytest.mark.parametrize('fn,request_model,args', [
    (suggest_roles,RoleAdviceRequest,([],)),
    (make_plan,ActivityPlanRequest,([],[])),(make_interview_guide,InterviewGuideRequest,([],[]))])
def test_internal_functions_explicitly_unavailable(fn, request_model, args):
    req = request_model(profile={'goal':'준비'})
    before = req.model_dump()
    with pytest.raises(FeatureUnavailableError):
        fn(req,*args,now=NOW)
    assert req.model_dump() == before


def test_server_error_hides_exception():
    from backend.main import server_error
    import asyncio
    response = asyncio.run(server_error(None, RuntimeError('private-value')))
    assert response.status_code == 500
    assert b'private-value' not in response.body


def test_basic_recommendation_internal_contract_and_missing_database_503():
    req = RecommendationRequest(profile={'interests': ['개발']})
    before = req.model_dump()
    result = recommend(req, validate_examples()['opportunities'], now=NOW)
    assert result.engine == 'rules'
    assert result.candidate_count == 1
    assert result.items[0].opportunity_id == 'synthetic-job'
    assert result.items[0].eligibility == 'unknown'
    assert req.model_dump() == before
    response = client.post('/api/v1/recommendations', json=req.model_dump(mode='json'))
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'FEATURE_UNAVAILABLE'
