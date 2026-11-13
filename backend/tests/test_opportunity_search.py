import copy
import json
import shutil
import sqlite3
import unicodedata
from contextlib import closing
from pathlib import Path
from random import Random

import pytest
from fastapi.testclient import TestClient

from backend import main, catalog_store, opportunity_query
from backend.importer import import_directory
from backend.opportunity_search import filter_opportunities
from shared.models import Opportunity, OpportunityType
from typing import get_args

MATCH_IDS = [f'synthetic-search-{n:03d}' for n in [22, 23, 24, 26, 31, 45]]


@pytest.fixture
def search_catalog(tmp_path, monkeypatch):
    examples = Path('contracts/examples')
    batch = tmp_path / 'batch'
    batch.mkdir()
    for name in ['sources', 'roles', 'resource_links']:
        (batch / f'{name}.json').write_bytes((examples / f'{name}.json').read_bytes())
    template = json.loads((examples / 'opportunities.json').read_text(encoding='utf-8'))[0]
    rows = []
    for n in range(1, 46):
        item = copy.deepcopy(template)
        item.update(id=f'synthetic-search-{n:03d}', type=['notice', 'job', 'event'][n % 3],
                    title=f'일반 합성 공고 {n:03d}', organization='가상 기관',
                    summary='검사 전용 합성 설명', tags=['일반'], subtype=None)
        rows.append(item)
    rows[21]['title'] = '검색표식 개발 프로젝트'
    rows[22]['organization'] = '검색표식 연구원'
    rows[23]['summary'] = '검색표식 대회 설명'
    rows[25]['title'] = '검색표식 마감공고'
    rows[25]['application'] = {'status': 'closed'}
    rows[30]['tags'] = ['검색표식', 'SQLD', 'AI', 'Cafe\u0301']
    rows[44]['tags'] = ['검색표식', 'C++', '50%_literal', 'Straße', 'ＡＩ']
    Random(16).shuffle(rows)
    (batch / 'opportunities.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    db = tmp_path / '검색 자료.db'
    import_directory(batch, db, mode='demo')
    monkeypatch.setattr(main.settings, 'database_url', 'sqlite:///' + str(db))
    monkeypatch.setattr(main.settings, 'data_mode', 'demo')
    originals = sorted([Opportunity.model_validate(row) for row in rows], key=lambda row: row.id)
    with TestClient(main.app) as client:
        yield client, db, originals


def page(client, params=None):
    response = client.get('/api/v1/opportunities', params=params)
    assert response.status_code == 200, response.text
    return response.json()


def ids(result):
    return [row['id'] for row in result['items']]


def test_unchanged_request_and_empty_queries(search_catalog):
    client, db, originals = search_catalog
    before = db.read_bytes()
    baseline = page(client)
    assert baseline == {'items': [item.model_dump(mode='json') for item in originals[:20]],
                        'total': 45, 'limit': 20, 'offset': 0}
    for q in ['', ' ', '\t\n  ', '\u3000\u00a0']:
        assert page(client, {'q': q}) == baseline
    assert db.read_bytes() == before


def test_match_beyond_default_first_page_and_filtered_total(search_catalog):
    client, _, _ = search_catalog
    assert not set(ids(page(client))) & set(MATCH_IDS)
    result = page(client, {'q': '없는검색어'})
    assert result == {'items': [], 'total': 0, 'limit': 20, 'offset': 0}
    matched = page(client, {'q': '검색표식', 'limit': 2})
    assert matched['total'] == 6 and ids(matched) == MATCH_IDS[:2]


@pytest.mark.parametrize('q,expected', [
    ('  개발\t기관  ', [22]), ('기관 개발', [22]), ('연구원', [23]), ('대회 설명', [24]),
    ('검색표식 SQLD', [31]), ('sqld', [31]), ('aI', [31, 45]), ('ＡＩ', [31, 45]),
    ('CAFÉ', [31]), ('strasse', [45]), ('C++', [45]), ('50%_literal', [45]),
    ('%', [45]), ('_', [45]), ("%' OR 1=1 --", []), ('null', []),
    (unicodedata.normalize('NFD', '검색표식'), [22, 23, 24, 26, 31, 45]),
])
def test_terms_unicode_case_and_literal_characters(search_catalog, q, expected):
    client, db, _ = search_catalog
    before = db.read_bytes()
    result = page(client, {'q': q, 'limit': 100})
    assert ids(result) == [f'synthetic-search-{n:03d}' for n in expected]
    assert result['total'] == len(expected)
    assert db.read_bytes() == before


def test_multiple_types_or_and_query_and_duplicates(search_catalog):
    client, _, _ = search_catalog
    params = [('q', '검색표식'), ('types', 'job'), ('types', 'event'), ('types', 'job')]
    result = page(client, params)
    assert ids(result) == [f'synthetic-search-{n:03d}' for n in [22, 23, 26, 31]]
    assert result['total'] == 4
    assert page(client, [('types', 'job')] * 20)['total'] == 15
    assert page(client, [('types', item) for item in get_args(OpportunityType)])['total'] == 45


@pytest.mark.parametrize('limit', [1, 2, 4, 20, 100])
def test_filtered_page_walk_has_no_gaps_or_duplicates(search_catalog, limit):
    client, _, _ = search_catalog
    seen = []
    for offset in range(0, 6, limit):
        result = page(client, {'q': '검색표식', 'limit': limit, 'offset': offset})
        assert (result['total'], result['limit'], result['offset']) == (6, limit, offset)
        seen.extend(ids(result))
    assert seen == MATCH_IDS and len(set(seen)) == 6


@pytest.mark.parametrize('offset', [6, 7, 100])
def test_filtered_offset_exceeded_keeps_actual_total(search_catalog, offset):
    result = page(search_catalog[0], {'q': '검색표식', 'offset': offset})
    assert result == {'items': [], 'total': 6, 'limit': 20, 'offset': offset}


def test_query_length_boundary(search_catalog):
    client, _, _ = search_catalog
    assert page(client, {'q': '가' * 200})['total'] == 0
    assert page(client, {'q': ' ' * 200})['total'] == 45
    response = client.get('/api/v1/opportunities', params={'q': 'private-input-' + '가' * 201})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'
    assert 'private-input-' not in response.text


@pytest.mark.parametrize('params', [
    [('types', '')], [('types', 'invalid-private-type')], [('types', 'job,event')],
    [('types', 'job'), ('types', '')], [('types', ' JOB ')],
    [('q', '검색'), ('limit', '0')], [('q', '검색'), ('offset', '-1')],
])
def test_invalid_search_parameters_are_safe_422(search_catalog, params):
    response = search_catalog[0].get('/api/v1/opportunities', params=params)
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'
    assert 'invalid-private-type' not in response.text


def test_detail_ignores_search_and_closed_items_are_not_removed(search_catalog):
    client, _, originals = search_catalog
    closed = next(item for item in originals if item.id.endswith('026'))
    assert closed.application.status == 'closed'
    result = page(client, {'q': '마감공고'})
    assert result['total'] == 1 and result['items'][0] == closed.model_dump(mode='json')
    response = client.get('/api/v1/opportunities/' + originals[0].id,
                          params={'q': 'not-matching', 'types': 'event'})
    assert response.status_code == 200
    assert response.json() == originals[0].model_dump(mode='json')


@pytest.mark.parametrize('damage', ['payload', 'duplicate_key', 'source', 'mode', 'schema', 'missing'])
def test_filter_cannot_hide_invalid_database(search_catalog, damage):
    client, db, _ = search_catalog
    page(client)  # Warm the reference-schema cache before tampering.
    if damage == 'missing':
        main.settings.database_url = 'sqlite:///' + str(db.parent / 'missing.db')
    else:
        with closing(sqlite3.connect(db)) as connection:
            if damage == 'payload':
                connection.execute('UPDATE opportunities SET payload=? WHERE id=?',
                                   ('{"secret":"private-db"}', 'synthetic-search-001'))
            elif damage == 'duplicate_key':
                payload = connection.execute('SELECT payload FROM opportunities LIMIT 1').fetchone()[0]
                connection.execute('UPDATE opportunities SET payload=?', ('{"id":"duplicated",' + payload[1:],))
            elif damage == 'source': connection.execute('DELETE FROM sources')
            elif damage == 'mode': connection.execute("UPDATE import_metadata SET mode='real'")
            else: connection.execute('ALTER TABLE opportunities ADD COLUMN unknown TEXT')
            connection.commit()
    before = db.read_bytes()
    response = client.get('/api/v1/opportunities', params={'q': 'no-match-would-hide-damage'})
    assert response.status_code == 503 and response.json()['error']['code'] == 'FEATURE_UNAVAILABLE'
    assert 'private-db' not in response.text and str(db) not in response.text
    assert db.read_bytes() == before
    assert not (db.parent / 'missing.db').exists()


def test_total_and_items_use_one_validated_read_and_see_next_update(search_catalog, monkeypatch):
    client, db, _ = search_catalog
    copy_db = db.parent / 'snapshot.db'
    shutil.copyfile(db, copy_db)
    monkeypatch.setattr(main.settings, 'database_url', 'sqlite:///' + str(copy_db))
    calls = []
    def read_then_update(settings):
        catalog = catalog_store.read_catalog(settings)
        calls.append(True)
        with closing(sqlite3.connect(copy_db)) as writer:
            payload = writer.execute('SELECT payload FROM opportunities WHERE id=?', ('synthetic-search-001',)).fetchone()[0]
            value = json.loads(payload)
            value['summary'] = '검색표식'
            writer.execute('UPDATE opportunities SET payload=? WHERE id=?', (json.dumps(value), value['id']))
            writer.commit()
        return catalog
    monkeypatch.setattr(opportunity_query, 'read_catalog', read_then_update)
    first = page(client, {'q': '검색표식', 'limit': 100})
    assert len(calls) == 1 and first['total'] == len(first['items']) == 6
    second = page(client, {'q': '검색표식', 'limit': 100})
    assert len(calls) == 2 and second['total'] == len(second['items']) == 7


def test_pure_filter_does_not_mutate_or_merge_fields(search_catalog):
    _, _, originals = search_catalog
    before = [row.model_dump_json() for row in originals]
    assert [row.id for row in filter_opportunities(reversed(originals), q='검색표식')] == MATCH_IDS
    assert [row.model_dump_json() for row in originals] == before
    split = originals[0].model_copy(update={'title': 'abc', 'organization': 'def', 'summary': 'x', 'tags': []})
    assert filter_opportunities([split], q='cde') == []


def test_disabled_search_does_not_read_database(search_catalog, monkeypatch):
    from shared.models import Capability
    client, _, _ = search_catalog
    monkeypatch.setitem(main.capability_flags, 'opportunities', Capability(
        enabled=False, implemented=True, unavailable_reason='disabled for test'))
    def forbidden(settings): raise AssertionError('disabled route read DB')
    monkeypatch.setattr(opportunity_query, 'read_catalog', forbidden)
    assert client.get('/api/v1/opportunities?q=검색표식').status_code == 503
