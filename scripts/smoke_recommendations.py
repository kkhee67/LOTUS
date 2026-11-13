"""Current-time local API smoke: validates the contract without fixing result count."""
import argparse
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from shared.models import RecommendationApiResponse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    url = urlparse(args.url)
    if url.scheme != 'http' or url.hostname not in ('localhost', '127.0.0.1') or url.username or url.password or url.query or url.fragment or url.path not in ('', '/'):
        parser.error('Use a dedicated local HTTP server base URL')
    body = json.dumps({'profile': {'interests': ['사업']}}).encode()
    request = Request(args.url.rstrip('/') + '/api/v1/recommendations', data=body,
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=10) as response:
        result = RecommendationApiResponse.model_validate_json(response.read())
    print(json.dumps({'status': 'ok', 'returned': len(result.items), 'candidates': result.candidate_count}))


if __name__ == '__main__':
    main()
