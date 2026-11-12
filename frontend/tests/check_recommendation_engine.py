"""Run captured, synthetic browser requests through a separate engine checkout."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path, help='Checkout containing the recommender and shared models')
    parser.add_argument('requests', type=Path, help='JSON array of POST bodies captured from the test browser')
    parser.add_argument('--scores', type=int, nargs='+', required=True, help='Expected scores, with 0 for no result')
    args = parser.parse_args()
    root = args.engine.resolve()
    sys.path.insert(0, str(root))

    from recommender.opportunities.service import recommend
    from shared.models import Opportunity, RecommendationRequest

    data = json.loads((root / 'contracts/examples/opportunities.json').read_text(encoding='utf-8'))[0]
    data.update(
        eligibility_rules=[], requirements=[], unresolved_conditions=[],
        requirements_coverage='partial', experience_required=None, fields=['software'],
        application={'status': 'open'},
        evidence=[{'id': 'field', 'field': 'fields', 'fact': '소프트웨어', 'source_url': data['source_url']}],
    )
    opportunity = Opportunity.model_validate(data)
    requests = json.loads(args.requests.read_text(encoding='utf-8'))
    now = datetime.fromisoformat('2026-11-12T22:09:00+09:00')
    for body, expected in zip(requests, args.scores, strict=True):
        request = RecommendationRequest.model_validate(body)
        result = recommend(request, [opportunity], now=now)
        scores = [entry.relevance_score for entry in result.items]
        expected_scores = [expected] if expected else []
        if scores != expected_scores:
            raise AssertionError(f'Expected scores {expected_scores}, got {scores}')
        print(f'preferred_job_fields={request.profile.preferred_job_fields!r}: {scores}')


if __name__ == '__main__':
    main()
