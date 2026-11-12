import copy

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.importer import import_directory
from shared.models import Capability


@pytest.fixture
def server(tmp_path, monkeypatch):
    db = tmp_path / 'real.db'
    import_directory('data/normalized', db, mode='real')
    monkeypatch.setattr(main.settings, 'database_url', 'sqlite:///' + str(db))
    monkeypatch.setattr(main.settings, 'data_mode', 'real')
    return TestClient(main.app), db


def test_main_real_list_detail_and_404(server):
    client, db = server
    before = db.read_bytes()
    response = client.get('/api/v1/opportunities?limit=1&offset=1')
    assert response.status_code == 200
    page = response.json()
    assert page['total'] == 3 and len(page['items']) == 1
    item = page['items'][0]
    detail = client.get('/api/v1/opportunities/' + item['id'])
    assert detail.status_code == 200 and detail.json() == item
    assert item['source_kind'] == 'real'
    assert client.get('/api/v1/opportunities/not-present').status_code == 404
    assert client.get('/api/v1/opportunities?offset=500').json()['items'] == []
    assert db.read_bytes() == before


def test_opportunities_and_recommendations_are_available(server):
    client, _ = server
    caps = client.get('/api/v1/capabilities').json()
    assert caps['opportunities'] == {'enabled': True, 'implemented': True, 'unavailable_reason': None}
    assert all(flag['enabled'] == (name == 'recommendations') and flag['implemented'] == (name in {'recommendations', 'resource-links'})
               for name, flag in caps.items() if name != 'opportunities')
    assert client.get('/api/v1/resource-links').status_code == 503
    for name in (item for item in main.FEATURES if item != 'recommendations'):
        assert client.post('/api/v1/' + name, json={'profile': {'goal': 'test'}}).status_code == 503


def test_main_disable_blocks_both_routes_before_db_access(server, monkeypatch):
    client, _ = server
    monkeypatch.setitem(main.capability_flags, 'opportunities',
                        Capability(enabled=False, implemented=True, unavailable_reason='test disabled'))
    def must_not_read(*args):
        raise AssertionError('disabled feature accessed DB')
    monkeypatch.setattr('backend.opportunity_query.read_opportunities', must_not_read)
    for path in ['/api/v1/opportunities', '/api/v1/opportunities/some-id']:
        response = client.get(path)
        assert response.status_code == 503
        assert response.json()['error']['code'] == 'FEATURE_UNAVAILABLE'


def test_main_db_missing_or_wrong_mode_is_safe(server, monkeypatch):
    client, db = server
    monkeypatch.setattr(main.settings, 'data_mode', 'demo')
    assert client.get('/api/v1/opportunities').status_code == 503
    monkeypatch.setattr(main.settings, 'database_url', 'sqlite:///' + str(db.parent / 'private-missing.db'))
    response = client.get('/api/v1/opportunities')
    assert response.status_code == 503
    assert 'private-missing' not in response.text
    assert not (db.parent / 'private-missing.db').exists()


@pytest.mark.parametrize('damage', ['names', 'implementation', 'reason', 'unsupported'])
def test_startup_flags_reject_unsupported_or_inconsistent_config(damage):
    flags = copy.deepcopy(main.capability_flags)
    if damage == 'names':
        flags.pop('opportunities')
    elif damage == 'implementation':
        flags['opportunities'] = Capability(enabled=False, implemented=False, unavailable_reason='old bootstrap')
    elif damage == 'reason':
        flags['opportunities'] = Capability(enabled=True, implemented=True, unavailable_reason='contradiction')
    else:
        flags['career-roles'] = Capability(enabled=True, implemented=True)
    with pytest.raises(RuntimeError):
        main.validate_capability_flags(flags)


def test_startup_allows_implemented_but_disabled():
    flags = copy.deepcopy(main.capability_flags)
    flags['opportunities'] = Capability(enabled=False, implemented=True, unavailable_reason='maintenance')
    main.validate_capability_flags(flags)


def test_no_duplicate_query_routes():
    def registered_paths(routes):
        for route in routes:
            yield getattr(route, 'path', None)
            included = getattr(route, 'original_router', None)
            if included is not None:
                yield from registered_paths(included.routes)
    paths = list(registered_paths(main.app.routes))
    for path in ['/api/v1/opportunities', '/api/v1/opportunities/{id}']:
        assert paths.count(path) == 1
