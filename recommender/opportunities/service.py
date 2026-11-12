"""Deterministic recommendations using supplied models and time only."""
from datetime import datetime
from pathlib import Path
import re
import unicodedata
from shared.models import (Opportunity, OptionsResponse, RecommendationItem, RecommendationReason,
                           RecommendationRequest, RecommendationResponse, RuleExpression, UserProfile)
from shared.rules import application_state

CATALOG = OptionsResponse.model_validate_json(
    (Path(__file__).resolve().parents[2] / 'shared/catalog.json').read_text(encoding='utf-8'))


def normalized(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r'(?<!\w)' + re.escape(normalized(phrase)) + r'(?!\w)', normalized(text)) is not None


def evaluate(expression: RuleExpression, profile: UserProfile) -> bool | None:
    """Three-valued evaluation: None represents missing information."""
    kind = expression.kind
    if kind in ('all', 'any', 'exception'):
        children = ([expression.base, *expression.alternatives]
                    if kind == 'exception' else expression.rules)
        values = [evaluate(child, profile) for child in children]
        if kind == 'all':
            return False if False in values else None if None in values else True
        return True if True in values else None if None in values else False
    if kind == 'age':
        if profile.age is None:
            return None
        return {'eq': profile.age == expression.value, 'gte': profile.age >= expression.value,
                'lte': profile.age <= expression.value}[expression.operator]
    if kind == 'education':
        value = profile.education_status
        if value == 'unknown' or 'unknown' in expression.values:
            return None
    else:
        value = getattr(profile, expression.field)
        if value is None:
            return None
    matched = normalized(value) in {normalized(x) for x in expression.values}
    return matched if expression.operator == 'in' else not matched


def eligibility(opportunity: Opportunity, profile: UserProfile) -> str:
    results = [evaluate(rule.expression, profile) for rule in opportunity.eligibility_rules]
    if False in results:
        return 'ineligible'
    # Text conditions cannot be proven fully represented by the structured rules.
    # Activity presence does not establish a required work-experience duration.
    if (None in results or opportunity.requirements_coverage != 'complete'
            or opportunity.unresolved_conditions or opportunity.requirements
            or opportunity.experience_required is not False):
        return 'unknown'
    return 'eligible'


def score(opportunity: Opportunity, profile: UserProfile) -> tuple[int, list[RecommendationReason]]:
    reasons = []
    points = 0
    for label, entries, weight, free_text in (
        ('관심 분야', profile.interests, 40, False),
        ('희망 직무', profile.preferred_job_fields, 40, False),
        ('목표', [profile.goal] if profile.goal else [], 20, True),
    ):
        matched = []
        for field in CATALOG.fields:
            aliases = [field.code, field.label, *field.aliases]
            if not any(contains_phrase(entry, alias) if free_text else normalized(entry) == normalized(alias)
                       for entry in entries for alias in aliases):
                continue
            for evidence in opportunity.evidence:
                if ((evidence.field == 'fields' and field.code in opportunity.fields
                         and any(contains_phrase(evidence.fact, alias) for alias in aliases))
                        or (evidence.field == 'activities'
                            and any(contains_phrase(evidence.fact, alias) for alias in aliases)
                            and any(contains_phrase(activity, alias) for activity in opportunity.activities for alias in aliases))):
                    matched.append(evidence.id)
        if matched:
            points += weight
            reasons.append(RecommendationReason(text=f'{label}와 공고의 분야·활동 근거가 일치합니다.',
                                                evidence_ids=sorted(set(matched))))
    if profile.major and normalized(profile.major) in {normalized(x) for x in opportunity.related_majors}:
        ids = sorted(e.id for e in opportunity.evidence if e.field == 'related_majors'
                     and contains_phrase(e.fact, profile.major))
        if ids:
            points += 15
            reasons.append(RecommendationReason(text='전공이 공고의 관련 전공과 일치합니다. 지원 자격 보장은 아닙니다.',
                                                evidence_ids=ids))
    return min(100, points), reasons


def recommend(request: RecommendationRequest, opportunities: list[Opportunity], *, now: datetime) -> RecommendationResponse:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('now must include a timezone')
    if len({item.id for item in opportunities}) != len(opportunities):
        raise ValueError('duplicate opportunity IDs')
    if len({item.source_kind for item in opportunities}) > 1:
        raise ValueError('real and synthetic data must not be mixed')
    if any(not set(item.fields) <= {field.code for field in CATALOG.fields} for item in opportunities):
        raise ValueError('unknown catalog field code')
    items = []
    for opportunity in opportunities:
        if request.types and opportunity.type not in request.types:
            continue
        cautions = []
        if opportunity.certification:
            if opportunity.certification.status != 'active':
                continue
            states = [application_state(session.application, now=now)
                      for session in opportunity.certification.exam_sessions]
            open_states = [state for state in states if state.status == 'open']
            if not open_states:
                cautions.append('운영 중인 자격증이나 확인된 접수 중 회차는 없습니다. 회차 일정을 원문에서 확인하세요.')
            for state in open_states:
                cautions.extend(state.cautions)
        else:
            state = application_state(opportunity.application, now=now)
            if state.status != 'open':
                continue
            cautions.extend(state.cautions)
        status = eligibility(opportunity, request.profile)
        if status == 'ineligible':
            continue
        points, reasons = score(opportunity, request.profile)
        if points < 15 or not reasons:
            continue
        if status == 'unknown':
            cautions.append('필수 조건 또는 입력 정보가 충분하지 않아 지원 자격을 확인해야 합니다.')
        cautions.append('관련성 점수는 합격 확률이 아닙니다. 최신 모집 내용과 최종 지원 자격은 원문에서 확인하세요.')
        items.append(RecommendationItem(opportunity_id=opportunity.id, relevance_score=points,
                                       eligibility=status, reasons=reasons, cautions=list(dict.fromkeys(cautions)),
                                       explanation_source='template'))
    items.sort(key=lambda item: (-item.relevance_score, item.eligibility != 'eligible', item.opportunity_id))
    return RecommendationResponse(items=items[:request.limit], candidate_count=len(items), engine='rules',
                                  warnings=['합성 예시 자료의 추천이며 실제 모집 정보가 아닙니다.']
                                  if items and opportunities[0].source_kind == 'synthetic' else [])
