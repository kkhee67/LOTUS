"""Deterministic recommendations using supplied models and time only."""
from datetime import datetime
import json
from pathlib import Path
from .policy import INTEREST_WEIGHT, JOB_WEIGHT, GOAL_WEIGHT, MAJOR_WEIGHT, MIN_SCORE, MAX_SCORE
from .text import normalized, phrases_pattern, positive_clauses, positive_mentions, profile_expression, ROLE_ALIASES, NEGATIVE
from shared.models import (Opportunity, OptionsResponse, RecommendationItem, RecommendationReason,
                           RecommendationRequest, RecommendationResponse, RuleExpression, UserProfile)
from shared.rules import application_state

CATALOG = OptionsResponse.model_validate_json(
    (Path(__file__).resolve().parents[2] / 'shared/catalog.json').read_text(encoding='utf-8'))

# Extra topic names are used for text evidence only, never as contract field codes.
TOPICS = {field.code: [field.code, field.label, *field.aliases] for field in CATALOG.fields}
for terms in json.loads((Path(__file__).resolve().parents[2] / 'shared/search_topics.json').read_text(encoding='utf-8')):
    if terms[0] not in TOPICS:
        TOPICS['ai' if 'AI' in terms else terms[0]] = terms

ProfileCriteria = list[tuple[str, int, list[str]]]

job_groups = json.loads((Path(__file__).resolve().parents[2] / 'shared/profile_jobs.json').read_text(encoding='utf-8'))
for roles in job_groups.values():
    for role, terms in roles.items():
        TOPICS[role] = [role, *terms]

INPUT_TOPICS: dict[str, set[str]] = {}
input_phrases = set()
for code, aliases in TOPICS.items():
    for alias in [*aliases, *ROLE_ALIASES.get(code, ())]:
        input_phrases.add(alias)
        INPUT_TOPICS.setdefault(normalized(alias).replace(' ', ''), set()).add(code)
GOAL_PHRASES = phrases_pattern(input_phrases)

# A broad interest may use evidence naming a specific occupation. The reverse
# would recommend a whole sector for a user who requested a particular job.
SECTOR_ROLES = {
    '보건': list(job_groups['보건·복지·돌봄']),
    '금융': [r for r in job_groups['금융·회계·법무'] if r != '법무 사무원'],
    '영상': ['영상 편집자', '촬영 스태프', '모션그래픽 디자이너', '콘텐츠 기획자', '웹툰 작가', '출판 편집자', '공연·전시 기획자'],
    'design': ['UX/UI 디자이너', '그래픽 디자이너', '브랜드 디자이너', '제품 디자이너', '웹 디자이너'],
    '광고': ['마케터', '디지털 마케터', 'SNS 운영 담당자', '홍보 담당자', '광고 기획자'],
    '공공행정': ['행정 사무원', '공무원', '공공기관 사무원', '학교 행정실 직원'],
    '교육': ['보육교사', '방과후 강사', '교육 운영 담당자', '교육 콘텐츠 개발자'],
    '건축': ['건축설계 담당자', '인테리어 디자이너', '건설 현장관리 담당자', '토목 기술자', '건축 CAD 담당자'],
    '전기': ['전기설비 기술자', '반도체 장비 기술자', '전자부품 조립원'],
    '기계': ['기계설계 기술자', 'CNC 가공 기술자', '자동차 정비사', '설비 유지보수 기술자'],
    '환경': ['환경관리 담당자', '신재생에너지 설비 기술자'],
    '물류': ['물류 운영 담당자', '물류센터 현장 직원', '지게차 운전원', '재고관리 담당자', '농산물 유통 담당자'],
    '관광': ['호텔 서비스 직원', '여행상품 기획자', '항공 지상직'],
    '식품': ['바리스타', '조리사', '제과제빵사', '영양사', '식음료 서비스 직원', '식품 연구개발 담당자', '식품 품질관리 담당자'],
    '진학': ['연구 보조원', '실험실 분석원'],
}
for sector, roles in SECTOR_ROLES.items():
    TOPICS[sector] = list(dict.fromkeys([*TOPICS[sector], *(alias for role in roles for alias in TOPICS[role])]))


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


def profile_topics(profile: UserProfile) -> ProfileCriteria:
    criteria = []
    for label, entries, weight, free_text in (
        ('관심 분야', profile.interests, INTEREST_WEIGHT, False),
        ('희망 직무', profile.preferred_job_fields, JOB_WEIGHT, False),
        ('목표', [profile.goal] if profile.goal else [], GOAL_WEIGHT, True),
    ):
        topics: set[str] = set()
        if free_text and entries:
            goal = normalized(entries[0]).replace('관련', ' 관련 ')
            for clause in positive_clauses(goal):
                for match in GOAL_PHRASES.finditer(clause):
                    topics.update(INPUT_TOPICS[match[1].replace(' ', '')])
        else:
            for entry in entries:
                if NEGATIVE.search(normalized(entry)):
                    continue
                expression = profile_expression(entry)
                matched = {code for part in (expression, *expression.split('·'))
                           for code in INPUT_TOPICS.get(part.strip().replace(' ', ''), ())}
                if matched:
                    topics.update(matched)
                elif len(expression) >= 2:
                    topics.add(expression)
        if topics:
            criteria.append((label, weight, sorted(topics)))
    return criteria


def score(opportunity: Opportunity, profile: UserProfile,
          criteria: ProfileCriteria | None = None) -> tuple[int, list[RecommendationReason]]:
    reasons = []
    points = 0
    if criteria is None:
        criteria = profile_topics(profile)
    for label, weight, topics in criteria:
        matched = []
        for code in topics:
            aliases = TOPICS.get(code, [code])
            for evidence in opportunity.evidence:
                if evidence.field not in ('fields', 'activities', 'summary') or not positive_mentions(evidence.fact, aliases):
                    continue
                if ((evidence.field == 'fields' and code in opportunity.fields)
                        or (evidence.field == 'activities' and any(positive_mentions(activity, aliases)
                                                                  for activity in opportunity.activities))
                        or (evidence.field == 'summary' and any(positive_mentions(value, aliases)
                                                               for value in (opportunity.title, opportunity.summary)))):
                    matched.append(evidence.id)
        if matched:
            points += weight
            reasons.append(RecommendationReason(text=f'{label}와 관련된 내용을 공고에서 확인했습니다.',
                                                evidence_ids=sorted(set(matched))))
    if profile.major and normalized(profile.major) in {normalized(x) for x in opportunity.related_majors}:
        ids = sorted(e.id for e in opportunity.evidence if e.field == 'related_majors'
                     and positive_mentions(e.fact, [profile.major]))
        if ids:
            points += MAJOR_WEIGHT
            reasons.append(RecommendationReason(text='전공이 공고의 관련 전공과 일치합니다. 지원 자격 보장은 아닙니다.',
                                                evidence_ids=ids))
    return min(MAX_SCORE, points), reasons


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
    criteria = profile_topics(request.profile)
    for opportunity in opportunities:
        if request.types and opportunity.type not in request.types:
            continue
        cautions = []
        if request.profile.goal and NEGATIVE.search(normalized(request.profile.goal)):
            cautions.append('목표의 부정·제외 표현은 해당 구절의 점수 가산을 보류합니다. 다른 입력으로 추천될 수 있으니 희망 분야를 확인하세요.')
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
            if opportunity.application.closes_at is None and opportunity.application.closes_on is None:
                cautions.append(
                    '마감일이 기재되지 않은 공고입니다. 마지막 자료 확인 시각 '
                    f'{opportunity.checked_at.isoformat()} 이후 모집이 끝났을 수 있으니 원문을 다시 확인하세요.')
        status = eligibility(opportunity, request.profile)
        if status == 'ineligible':
            continue
        points, reasons = score(opportunity, request.profile, criteria)
        if points < MIN_SCORE or not reasons:
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
