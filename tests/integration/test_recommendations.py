from datetime import datetime, timedelta
import socket
import pytest
from shared.models import Opportunity, RecommendationRequest, UserProfile, RecommendationApiItem
from recommender.opportunities.service import recommend, evaluate
from scripts.validate_examples import load

NOW = datetime.fromisoformat('2026-11-11T12:00:00+09:00')


def opportunity(**updates):
    data = load('opportunities.json')[0]
    data.update(eligibility_rules=[], requirements=[], unresolved_conditions=[],
                requirements_coverage='complete', experience_required=False,
                fields=['software'], related_majors=['컴퓨터공학'],
                evidence=[{'id': 'field', 'field': 'fields', 'fact': '소프트웨어', 'source_url': data['source_url']},
                          {'id': 'major', 'field': 'related_majors', 'fact': '컴퓨터공학', 'source_url': data['source_url']},
                          {'id': 'experience', 'field': 'experience_required', 'fact': '경력 무관', 'source_url': data['source_url']},
                          {'id': 'rule', 'field': 'eligibility_rules', 'fact': '합성 조건', 'source_url': data['source_url']}])
    data.update(updates)
    return Opportunity.model_validate(data)


def run(items=None, **profile):
    return recommend(RecommendationRequest(profile=profile or {'interests': ['개발']}),
                     [opportunity()] if items is None else items, now=NOW)


@pytest.mark.parametrize('profile,points', [({'interests': ['개발']}, 40),
    ({'preferred_job_fields': ['software']}, 40), ({'goal': '개발 프로젝트 참여'}, 20),
    ({'major': '컴퓨터공학'}, 15), ({'interests': ['미지분야']}, 0), ({'goal': '개발자'}, 0),
    ({'interests': ['개발', '개발']}, 40),
    ({'interests': ['개발'], 'preferred_job_fields': ['개발'], 'goal': '개발', 'major': '컴퓨터공학'}, 100)])
def test_minimal_inputs_weights_and_unknowns(profile, points):
    result = run(**profile)
    assert (result.items[0].relevance_score if result.items else 0) == points


def test_interest_outweighs_major_and_irrelevant_items_are_not_padding():
    design = opportunity(id='design', fields=['design'], related_majors=[], experience_required=None,
                         evidence=[{'id': 'design-ev', 'field': 'fields', 'fact': '디자인', 'source_url': 'https://example.org'}])
    result = run([opportunity(), design], major='컴퓨터공학', interests=['디자인'])
    assert [x.relevance_score for x in result.items] == [40, 15]
    assert run([opportunity(evidence=[], experience_required=None)]).items == []


@pytest.mark.parametrize('coverage,requirements,experience,expected', [
    ('complete', [], False, 'eligible'), ('partial', [], False, 'unknown'),
    ('unknown', [], False, 'unknown'), ('complete', ['병역 필수'], False, 'unknown'),
    ('complete', [], None, 'unknown'), ('complete', [], True, 'unknown')])
def test_eligibility_never_proves_text_only_or_experience_conditions(coverage, requirements, experience, expected):
    result = run([opportunity(requirements_coverage=coverage, requirements=requirements, experience_required=experience)])
    assert result.items[0].eligibility == expected


def ruled(expression):
    return opportunity(eligibility_rules=[{'id': 'r', 'summary': '합성 조건', 'expression': expression, 'evidence_ids': ['rule']}])


@pytest.mark.parametrize('kind,values,expected', [
    ('all', [True, None], None), ('all', [False, None], False), ('all', [True, True], True),
    ('any', [False, None], None), ('any', [True, None], True), ('any', [False, False], False),
    ('exception', [False, True], True), ('exception', [False, None], None), ('exception', [False, False], False)])
def test_three_valued_nested_rules(kind, values, expected):
    leaves = {True: {'kind': 'age', 'operator': 'gte', 'value': 20},
              False: {'kind': 'age', 'operator': 'lte', 'value': 19},
              None: {'kind': 'text', 'field': 'school_id', 'operator': 'in', 'values': ['synthetic-school']}}
    children = [leaves[value] for value in values]
    expr = {'kind': kind, 'rules': children} if kind != 'exception' else {'kind': kind, 'base': children[0], 'alternatives': children[1:]}
    rule = ruled(expr).eligibility_rules[0].expression
    assert evaluate(rule, UserProfile(goal='준비', age=25)) is expected


def test_required_failure_excluded_missing_unknown_and_residence_separate():
    item = ruled({'kind': 'text', 'field': 'residence_region', 'operator': 'in', 'values': ['서울']})
    assert not run([item], interests=['개발'], residence_region='부산', preferred_job_regions=['서울']).items
    assert run([item], interests=['개발'], preferred_job_regions=['서울']).items[0].eligibility == 'unknown'
    assert run([item], interests=['개발'], residence_region='서울').items[0].eligibility == 'eligible'


def test_school_and_age_do_not_change_relevance_and_activities_are_not_invented():
    for extra in ({'school_name': '가상학교', 'age': 19}, {'school_name': '다른가상학교', 'age': 50},
                  {'experience_status': 'none'}, {'experience_status': 'unknown'}):
        assert run(interests=['개발'], **extra).items[0].relevance_score == 40


@pytest.mark.parametrize('application,count', [
    ({'status': 'closed'}, 0), ({'status': 'unknown'}, 0),
    ({'status': 'upcoming', 'opens_on': '2026-11-12'}, 0),
    ({'status': 'open', 'closes_at': (NOW-timedelta(microseconds=1)).isoformat()}, 0),
    ({'status': 'open', 'closes_at': NOW.isoformat()}, 0),
    ({'status': 'open', 'closes_at': (NOW+timedelta(microseconds=1)).isoformat()}, 1),
    ({'status': 'open', 'closes_on': '2026-11-11'}, 1),
    ({'status': 'open', 'closes_on': '2026-11-10'}, 0)])
def test_application_boundaries(application, count):
    result = run([opportunity(application=application)])
    assert len(result.items) == count
    if application.get('closes_on') == '2026-11-11':
        assert any('마감일 당일' in x for x in result.items[0].cautions)


@pytest.mark.parametrize('status,sessions,count', [('active', [], 1), ('active', ['closed'], 1),
    ('active', ['upcoming'], 1), ('active', ['open'], 1), ('inactive', [], 0), ('unknown', [], 0)])
def test_certification_operation_is_not_session_application(status, sessions, count):
    item = opportunity(type='certification', application={}, certification={'status': status, 'issuer': '가상기관',
        'exam_sessions': [{'id': str(i), 'name': '합성회차', 'application': {'status': state},
                           'source_url': 'https://example.org', 'checked_at': NOW} for i, state in enumerate(sessions)]})
    result = run([item])
    assert len(result.items) == count
    if count:
        assert any('접수 중 회차는 없습니다' in x for x in result.items[0].cautions) == ('open' not in sessions)


def test_sort_limit_count_types_and_evidence_references():
    items = [opportunity(id='z'), opportunity(id='a'), opportunity(id='0', requirements_coverage='unknown')]
    req = RecommendationRequest(profile={'interests': ['개발']}, limit=2)
    result = recommend(req, items, now=NOW)
    assert [x.opportunity_id for x in result.items] == ['a', 'z']
    assert result.candidate_count == 3
    for item in result.items:
        original = next(o for o in items if o.id == item.opportunity_id)
        assert RecommendationApiItem(recommendation=item, opportunity=original)
    assert not recommend(RecommendationRequest(profile=req.profile, types=['event']), items, now=NOW).items
    assert run([]).candidate_count == 0


def test_determinism_input_preservation_and_no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError('network forbidden')
    monkeypatch.setattr(socket, 'socket', fail)
    item = opportunity()
    req = RecommendationRequest(profile={'interests': ['개발']}, allow_external_ai=False)
    before = (req.model_dump_json(), item.model_dump_json())
    result = recommend(req, [item], now=NOW)
    assert result == recommend(req, [item], now=NOW)
    assert before == (req.model_dump_json(), item.model_dump_json())
    assert result.engine == 'rules' and result.items[0].explanation_source == 'template'
    req.allow_external_ai = True
    assert recommend(req, [item], now=NOW) == result


def test_invalid_batch_rejected_and_naive_time_rejected_even_when_empty():
    req = RecommendationRequest(profile={'goal': '개발'})
    for items in ([opportunity(), opportunity()], [opportunity(), opportunity(id='real', source_kind='real')],
                  [opportunity(fields=['not-in-catalog'])]):
        with pytest.raises(ValueError):
            recommend(req, items, now=NOW)
    with pytest.raises(ValueError):
        recommend(req, [], now=datetime(2026, 11, 11))

@pytest.mark.parametrize('expr,profile,expected', [
    ({'kind': 'age', 'operator': 'eq', 'value': 25}, {'age': 25}, True),
    ({'kind': 'age', 'operator': 'eq', 'value': 25}, {}, None),
    ({'kind': 'education', 'operator': 'in', 'values': ['graduated']}, {'education_status': 'graduated'}, True),
    ({'kind': 'education', 'operator': 'not_in', 'values': ['graduated']}, {}, None),
    ({'kind': 'text', 'field': 'major', 'operator': 'not_in', 'values': ['디자인']}, {'major': '컴퓨터공학'}, True),
    ({'kind': 'all', 'rules': [{'kind': 'age', 'operator': 'gte', 'value': 18},
      {'kind': 'exception', 'base': {'kind': 'age', 'operator': 'lte', 'value': 29},
       'alternatives': [{'kind': 'text', 'field': 'school_id', 'operator': 'in', 'values': ['synthetic-school']}]}]},
     {'age': 40, 'school_id': 'synthetic-school'}, True),
])
def test_leaf_and_nested_exception_rules(expr, profile, expected):
    item = ruled(expr)
    assert evaluate(item.eligibility_rules[0].expression, UserProfile(goal='준비', **profile)) is expected


def test_unrelated_evidence_cannot_justify_field_or_major_score():
    item = opportunity(evidence=[{'id': 'wrong', 'field': 'fields', 'fact': '디자인', 'source_url': 'https://example.org'},
                                {'id': 'wrong-major', 'field': 'related_majors', 'fact': '다른 전공', 'source_url': 'https://example.org'}],
                       experience_required=None)
    assert not run([item], interests=['개발'], major='컴퓨터공학').items


def test_unresolved_conditions_and_activity_states_never_prove_experience():
    item = opportunity(requirements_coverage='partial', unresolved_conditions=['필수 병역 조건'])
    assert run([item]).items[0].eligibility == 'unknown'
    item = opportunity(experience_required=True)
    for profile in ({'experience_status': 'none'}, {'experience_status': 'unknown'},
                    {'experience_status': 'provided', 'experiences': [{'id': 'synthetic-exp', 'kind': 'course_project', 'title': '가상 수업'}]}):
        assert run([item], interests=['개발'], **profile).items[0].eligibility == 'unknown'
