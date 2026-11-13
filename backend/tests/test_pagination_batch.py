"""Exercise real importer/DB/main routes with 30 explicitly synthetic records."""
import copy
import json
from pathlib import Path
from random import Random

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.importer import import_directory
from shared.models import Opportunity, Page


@pytest.fixture
def thirty_opportunities(tmp_path, monkeypatch):
    examples = Path('contracts/examples')
    batch = tmp_path / 'synthetic-batch'
    batch.mkdir()
    for name in ['sources', 'roles', 'resource_links']:
        (batch / f'{name}.json').write_bytes((examples / f'{name}.json').read_bytes())
    template = json.loads((examples / 'opportunities.json').read_text(encoding='utf-8'))[0]
    items = []
    for index in range(30):
        item = copy.deepcopy(template)
        item['id'] = f'synthetic-page-{index + 1:03d}'
        item['title'] = f'페이지 검사 전용 합성 공고 {index + 1:03d}'
        items.append(item)
    Random(7).shuffle(items)  # Ensure insertion order cannot accidentally pass ID sorting.
    (batch / 'opportunities.json').write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
    db = tmp_path / 'synthetic.db'
    import_directory(batch, db, mode='demo')
    before = db.read_bytes()
    monkeypatch.setattr(main.settings, 'database_url', 'sqlite:///' + str(db))
    monkeypatch.setattr(main.settings, 'data_mode', 'demo')
    originals = sorted([Opportunity.model_validate(item) for item in items], key=lambda item: item.id)
    with TestClient(main.app) as client:
        yield client, originals
    assert db.read_bytes() == before, 'Read-only pagination changed the temporary DB'


def get_page(client, **params):
    response = client.get('/api/v1/opportunities', params=params)
    assert response.status_code == 200
    return Page[Opportunity].model_validate(response.json())


def test_default_twenty_then_last_ten(thirty_opportunities):
    client, originals = thirty_opportunities
    first = get_page(client)
    last = get_page(client, offset=20)
    assert (first.limit, first.offset, len(first.items), first.total) == (20, 0, 20, 30)
    assert (last.limit, last.offset, len(last.items), last.total) == (20, 20, 10, 30)
    assert first.items + last.items == originals


@pytest.mark.parametrize('limit', [1, 7, 20, 30, 100])
def test_every_page_has_no_duplicates_or_gaps(thirty_opportunities, limit):
    client, originals = thirty_opportunities
    seen = []
    for offset in range(0, 30, limit):
        page = get_page(client, limit=limit, offset=offset)
        assert (page.total, page.limit, page.offset) == (30, limit, offset)
        assert page.items == originals[offset:offset + limit]
        seen.extend(page.items)
    assert seen == originals
    assert len(seen) == len({item.id for item in seen}) == 30
    assert all(item.source_kind == 'synthetic' for item in seen)


@pytest.mark.parametrize('offset', [30, 31, 100])
def test_end_and_beyond_end_are_empty_success(thirty_opportunities, offset):
    client, _ = thirty_opportunities
    page = get_page(client, offset=offset)
    assert page.items == [] and page.total == 30
    assert page.offset == offset and page.limit == 20


def test_repeating_pages_preserves_order_and_payload(thirty_opportunities):
    client, _ = thirty_opportunities
    expected = client.get('/api/v1/opportunities?limit=7&offset=14')
    assert expected.status_code == 200
    for _ in range(3):
        response = client.get('/api/v1/opportunities?limit=7&offset=14')
        assert response.status_code == 200 and response.json() == expected.json()


def test_every_listed_item_matches_detail_original(thirty_opportunities):
    client, originals = thirty_opportunities
    for original in originals:
        response = client.get('/api/v1/opportunities/' + original.id)
        assert response.status_code == 200
        assert response.json() == original.model_dump(mode='json')


def test_nonexistent_thirty_first_item_is_404(thirty_opportunities):
    client, _ = thirty_opportunities
    response = client.get('/api/v1/opportunities/synthetic-page-031')
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'NOT_FOUND'
