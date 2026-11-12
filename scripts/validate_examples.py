import json
from pathlib import Path
from pydantic import TypeAdapter
from shared.models import (
    Opportunity, Source, RoleProfile, ResourceLink, RecommendationRequest,
    RecommendationResponse, RecommendationApiResponse, RoleAdviceRequest,
    RoleAdviceResponse, ActivityPlanRequest, ActivityPlanResponse,
    InterviewGuideRequest, InterviewGuideResponse,
)
from shared.validation import validate_dataset

ROOT = Path(__file__).resolve().parents[1] / 'contracts/examples'


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def validate_examples():
    dataset = {
        name: TypeAdapter(list[model]).validate_python(load(f'{name}.json'))
        for name, model in [('sources', Source), ('opportunities', Opportunity),
                            ('roles', RoleProfile), ('resource_links', ResourceLink)]
    }
    validate_dataset(**dataset)
    assert all(x.source_kind == 'synthetic' for values in dataset.values() for x in values)
    RecommendationRequest.model_validate(load('recommendation_request.json')['request'])
    response = RecommendationResponse.model_validate(load('recommendation_response.json'))
    api_response = RecommendationApiResponse.model_validate(load('recommendation_api_response.json'))
    assert [x.recommendation for x in api_response.items] == response.items
    originals = {x.id: x for x in dataset['opportunities']}
    assert all(x.opportunity == originals[x.opportunity.id] for x in api_response.items)
    for name, req, res in [('role_advice', RoleAdviceRequest, RoleAdviceResponse),
                           ('activity_plan', ActivityPlanRequest, ActivityPlanResponse),
                           ('interview_guide', InterviewGuideRequest, InterviewGuideResponse)]:
        pair = load(f'{name}.json')
        request = req.model_validate(pair['request'])
        result = res.model_validate(pair['response'])
        if name == 'role_advice':
            role_ids = {r.id for r in dataset['roles']}
            source_ids = {s.id for s in dataset['sources']}
            assert all(x.role_id in role_ids and set(x.source_ids) <= source_ids for x in result.items)
        elif name == 'activity_plan':
            assert all(x.opportunity_id is None or x.opportunity_id in originals for x in result.steps)
        else:
            experience_ids = {e.id for e in request.profile.experiences}
            assert all(set(x.experience_ids) <= experience_ids for x in result.questions)
    return dataset


if __name__ == '__main__':
    data = validate_examples()
    print('Synthetic examples and references validated:', {k: len(v) for k, v in data.items()})
