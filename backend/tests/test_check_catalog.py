import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from backend.importer import import_directory

ROOT = Path(__file__).resolve().parents[2]


def run_check(db, *, mode='demo', **overrides):
    env = os.environ.copy()
    env.update(DATABASE_URL='sqlite:///' + str(db), DATA_MODE=mode,
               CORS_ORIGINS='http://localhost:5173')
    env.update(overrides)
    result = subprocess.run([sys.executable, '-m', 'backend.check_catalog'], cwd=ROOT,
                            env=env, capture_output=True, text=True, timeout=15,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    assert result.stderr == ''
    assert 'private-' not in result.stdout
    assert str(db) not in result.stdout
    return result.returncode, json.loads(result.stdout)


@pytest.mark.parametrize('mode,directory,counts', [
    ('demo', 'contracts/examples', {'sources': 1, 'opportunities': 3, 'roles': 1, 'resource_links': 1}),
    ('real', 'data/normalized', {'sources': 1, 'opportunities': 3, 'roles': 0, 'resource_links': 0}),
])
def test_actual_cli_validates_catalog_without_writing(tmp_path, mode, directory, counts):
    db = tmp_path / 'catalog.db'
    import_directory(directory, db, mode=mode)
    before = db.read_bytes()
    code, data = run_check(db, mode=mode)
    assert code == 0 and data == {'status': 'ok', 'data_mode': mode, 'counts': counts}
    assert db.read_bytes() == before


def test_missing_database_is_not_created(tmp_path):
    db = tmp_path / 'private-parent' / 'missing.db'
    code, data = run_check(db)
    assert code == 1 and data == {'status': 'unavailable', 'code': 'CATALOG_UNAVAILABLE'}
    assert not db.parent.exists()


@pytest.mark.parametrize('damage', ['mode', 'schema', 'payload', 'references', 'locked'])
def test_damaged_or_unavailable_database_fails_safely(tmp_path, damage):
    db = tmp_path / 'private-catalog.db'
    import_directory('contracts/examples', db, mode='demo')
    mode = 'demo'
    lock = None
    if damage == 'mode':
        mode = 'real'
    elif damage == 'locked':
        lock = sqlite3.connect(db)
    else:
        with sqlite3.connect(db) as connection:
            if damage == 'schema':
                connection.execute('PRAGMA user_version=99')
            elif damage == 'payload':
                connection.execute('UPDATE opportunities SET payload=?', ('{"secret":"private-payload"}',))
            else:
                connection.execute('DELETE FROM opportunities_sources')
    before = db.read_bytes()
    # On POSIX, closing another descriptor for this file can release process locks.
    # Read bytes before acquiring the lock and after releasing it, never in between.
    if lock:
        lock.execute('BEGIN EXCLUSIVE')
    try:
        code, data = run_check(db, mode=mode)
        assert code == 1 and data['code'] == 'CATALOG_UNAVAILABLE'
    finally:
        if lock:
            lock.rollback()
            lock.close()
    assert db.read_bytes() == before


@pytest.mark.parametrize('overrides', [
    {'DATA_MODE': 'private-invalid-mode'}, {'CORS_ORIGINS': 'private-invalid-origin'},
])
def test_invalid_configuration_returns_safe_exit_code(tmp_path, overrides):
    code, data = run_check(tmp_path / 'missing.db', **overrides)
    assert code == 2 and data == {'status': 'invalid_configuration', 'code': 'CONFIGURATION_ERROR'}


def test_valid_empty_catalog_is_distinct_from_missing_database(tmp_path):
    batch = tmp_path / 'empty-batch'
    batch.mkdir()
    for name in ['sources', 'opportunities', 'roles', 'resource_links']:
        (batch / f'{name}.json').write_text('[]', encoding='utf-8')
    db = tmp_path / 'empty.db'
    import_directory(batch, db, mode='demo')
    code, data = run_check(db)
    assert code == 0 and data['status'] == 'ok'
    assert data['counts'] == {'sources': 0, 'opportunities': 0, 'roles': 0, 'resource_links': 0}


def test_unexpected_check_failure_does_not_print_exception(monkeypatch, capsys):
    from backend import check_catalog
    monkeypatch.setattr(check_catalog, 'Settings', lambda: object())
    def fail(settings):
        raise RuntimeError('private-internal-error')
    monkeypatch.setattr(check_catalog, 'read_catalog', fail)
    assert check_catalog.main() == 3
    output = capsys.readouterr()
    assert output.err == '' and 'private-' not in output.out
    assert json.loads(output.out) == {'status': 'error', 'code': 'CHECK_FAILED'}
