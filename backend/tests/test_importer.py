import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from backend.importer import ImportFailure, MODELS, database_path, import_directory


@pytest.fixture
def batch(tmp_path):
    directory = tmp_path / 'input'
    directory.mkdir()
    for table in MODELS:
        shutil.copyfile(Path('contracts/examples') / f'{table}.json', directory / f'{table}.json')
    return directory


def edit(batch, table, mutate):
    path = batch / f'{table}.json'
    value = json.loads(path.read_text(encoding='utf-8'))
    mutate(value)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


def snapshot(db):
    with sqlite3.connect(db) as connection:
        return list(connection.iterdump())


def test_insert_idempotent_update_and_no_deletion(batch, tmp_path):
    db = tmp_path / 'test.db'
    originals = {p.name: p.read_bytes() for p in batch.iterdir()}
    first = import_directory(batch, db, mode='demo')
    assert first['counts']['opportunities'] == {'inserted': 3, 'updated': 0, 'unchanged': 0}
    before = snapshot(db)
    second = import_directory(batch, db, mode='demo')
    assert second['counts']['opportunities'] == {'inserted': 0, 'updated': 0, 'unchanged': 3}
    assert snapshot(db) == before
    assert originals == {p.name: p.read_bytes() for p in batch.iterdir()}
    edit(batch, 'opportunities', lambda rows: rows[0].update(title='Changed synthetic title'))
    result = import_directory(batch, db, mode='demo')
    assert result['counts']['opportunities']['updated'] == 1
    edit(batch, 'opportunities', lambda rows: rows.clear())
    import_directory(batch, db, mode='demo')
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT count(*) FROM opportunities').fetchone()[0] == 3
        payload = connection.execute("SELECT payload FROM opportunities WHERE id='synthetic-job'").fetchone()[0]
        assert json.loads(payload)['title'] == 'Changed synthetic title'
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []


@pytest.mark.parametrize('problem', ['duplicate', 'missing_source', 'unknown_field', 'extra_field',
    'mixed', 'missing_file', 'malformed', 'duplicate_key', 'not_array', 'invalid_utf8'])
def test_invalid_batch_preserves_db_and_does_not_create_new(batch, tmp_path, problem):
    db = tmp_path / 'existing.db'
    import_directory(batch, db, mode='demo')
    before = db.read_bytes()
    if problem == 'duplicate':
        edit(batch, 'opportunities', lambda rows: rows.append(rows[0]))
    elif problem == 'missing_source':
        edit(batch, 'roles', lambda rows: rows[0].update(source_ids=['absent']))
    elif problem == 'unknown_field':
        edit(batch, 'opportunities', lambda rows: rows[0].update(fields=['not-a-code']))
    elif problem == 'extra_field':
        edit(batch, 'sources', lambda rows: rows[0].update(secret='private-test-value'))
    elif problem == 'mixed':
        edit(batch, 'sources', lambda rows: rows[0].update(source_kind='real'))
    elif problem == 'missing_file':
        (batch / 'roles.json').unlink()
    elif problem == 'invalid_utf8':
        (batch / 'sources.json').write_bytes(b'\xff')
    else:
        text = {'malformed': '[', 'duplicate_key': '[{"id":"a","id":"b"}]', 'not_array': '{}'}[problem]
        (batch / 'sources.json').write_text(text, encoding='utf-8')
    for target in [db, tmp_path / 'new.db']:
        with pytest.raises(ImportFailure):
            import_directory(batch, target, mode='demo')
    assert db.read_bytes() == before
    assert not (tmp_path / 'new.db').exists()


def test_runtime_sql_failure_rolls_back_prior_updates(batch, tmp_path):
    db = tmp_path / 'rollback.db'
    import_directory(batch, db, mode='demo')
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TRIGGER reject_update BEFORE UPDATE ON opportunities BEGIN SELECT RAISE(ABORT, 'private-test-value'); END")
    before = snapshot(db)
    edit(batch, 'sources', lambda rows: rows[0].update(name='First update must roll back'))
    edit(batch, 'opportunities', lambda rows: rows[0].update(title='Trigger failure'))
    with pytest.raises(ImportFailure, match='기존 자료는 보존') as error:
        import_directory(batch, db, mode='demo')
    assert 'private-test-value' not in str(error.value)
    assert snapshot(db) == before


def test_mode_separation_between_batches(batch, tmp_path):
    db = tmp_path / 'demo.db'
    import_directory(batch, db, mode='demo')
    before = snapshot(db)
    # Synthetic test data simulating real-mode metadata, never published as real data.
    for table in MODELS:
        edit(batch, table, lambda rows: [row.update(source_kind='real') for row in rows])
    with pytest.raises(ImportFailure):
        import_directory(batch, db, mode='demo')
    with pytest.raises(ImportFailure, match='별도 DB'):
        import_directory(batch, db, mode='real')
    assert snapshot(db) == before
    assert import_directory(batch, tmp_path / 'separate.db', mode='real')['mode'] == 'real'


def test_empty_batch_never_deletes_existing(batch, tmp_path):
    db = tmp_path / 'empty.db'
    import_directory(batch, db, mode='demo')
    before = snapshot(db)
    for table in MODELS:
        (batch / f'{table}.json').write_text('[]', encoding='utf-8')
    result = import_directory(batch, db, mode='demo')
    assert all(all(count == 0 for count in stats.values()) for stats in result['counts'].values())
    assert snapshot(db) == before


@pytest.mark.parametrize('kind', ['unknown_version', 'unmanaged', 'locked'])
def test_existing_db_protected(batch, tmp_path, kind):
    db = tmp_path / 'protected.db'
    with sqlite3.connect(db) as connection:
        if kind == 'unknown_version':
            connection.execute('PRAGMA user_version=99')
        else:
            connection.execute('CREATE TABLE previous_work (value TEXT)')
    before = db.read_bytes()
    lock = sqlite3.connect(db)
    try:
        if kind == 'locked':
            lock.execute('BEGIN EXCLUSIVE')
        with pytest.raises(ImportFailure):
            import_directory(batch, db, mode='demo')
    finally:
        lock.rollback()
        lock.close()
    assert db.read_bytes() == before


def test_changed_reference_links_and_retained_sources(batch, tmp_path):
    db = tmp_path / 'refs.db'
    import_directory(batch, db, mode='demo')
    edit(batch, 'sources', lambda rows: rows.append({**rows[0], 'id':'second-source'}))
    edit(batch, 'opportunities', lambda rows: rows[0].update(source_ids=['second-source']))
    import_directory(batch, db, mode='demo')
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT source_id FROM opportunities_sources WHERE item_id='synthetic-job'").fetchall() == [('second-source',)]
        assert connection.execute('SELECT count(*) FROM sources').fetchone()[0] == 2


def test_cli_safe_output_and_exit_codes(batch, tmp_path):
    command = [sys.executable, '-m', 'backend.importer', '--input-dir', str(batch),
               '--database', str(tmp_path / 'cli.db'), '--mode', 'demo']
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0
    assert json.loads(result.stdout)['counts']['opportunities']['inserted'] == 3
    edit(batch, 'sources', lambda rows: rows[0].update(secret='private-test-value'))
    result = subprocess.run(command, capture_output=True)
    assert result.returncode == 1
    assert b'IMPORT_FAILED' in result.stderr
    assert b'private-test-value' not in result.stderr
    assert b'Traceback' not in result.stderr


def test_database_url():
    assert database_path('sqlite:///runtime/test.db').name == 'test.db'
    for url in ['postgres://private', 'sqlite:///:memory:', 'sqlite:///', 'sqlite:///test.db?mode=ro']:
        with pytest.raises(ImportFailure):
            database_path(url)


# Added during recipient-side review; the delivered tests above are unchanged.
@pytest.mark.parametrize('damage', ['schema', 'column_mode', 'missing_link', 'orphan_link'])
def test_rejects_inconsistent_existing_db_without_changes(batch, tmp_path, damage):
    db = tmp_path / 'inconsistent.db'
    import_directory(batch, db, mode='demo')
    with sqlite3.connect(db) as connection:
        if damage == 'schema':
            # Keep version=1 and data but remove the FK/PK constraints.
            connection.execute('ALTER TABLE opportunities_sources RENAME TO old_links')
            connection.execute('CREATE TABLE opportunities_sources (item_id TEXT, source_id TEXT)')
            connection.execute('INSERT INTO opportunities_sources SELECT * FROM old_links')
            connection.execute('DROP TABLE old_links')
        elif damage == 'column_mode':
            connection.execute("UPDATE opportunities SET source_kind='real' WHERE id='synthetic-job'")
        elif damage == 'missing_link':
            connection.execute("DELETE FROM opportunities_sources WHERE item_id='synthetic-job'")
        else:
            # A distinct connection defaults to FK enforcement off, as manual tools may do.
            connection.execute("INSERT INTO opportunities_sources VALUES ('missing-item', 'missing-source')")
    before = snapshot(db)
    command = [sys.executable, '-m', 'backend.importer', '--input-dir', str(batch),
               '--database', str(db), '--mode', 'demo']
    result = subprocess.run(command, capture_output=True)
    assert result.returncode == 1
    assert b'IMPORT_FAILED' in result.stderr
    assert b'Traceback' not in result.stderr
    assert snapshot(db) == before


@pytest.mark.parametrize('field', ['opens_on', 'closes_on', 'published_on', 'starts_on', 'ends_on', 'exam_on'])
def test_date_only_timestamp_input_preserves_existing_db(batch, tmp_path, field):
    db = tmp_path / 'date-validation.db'
    import_directory(batch, db, mode='demo')
    before = snapshot(db)
    def damage(rows):
        value = '2026-11-12T00:00:00+09:00'
        if field in ('opens_on', 'closes_on'):
            rows[0]['application'] = {'status': 'unknown', field: value}
        elif field == 'published_on':
            rows[0]['published_at'] = None
            rows[0][field] = value
        elif field in ('starts_on', 'ends_on'):
            rows[0]['event_schedule'] = {field: value}
        else:
            rows[1]['certification']['exam_sessions'][0][field] = value
    edit(batch, 'opportunities', damage)
    with pytest.raises(ImportFailure):
        import_directory(batch, db, mode='demo')
    assert snapshot(db) == before
    fresh = tmp_path / 'must-not-exist.db'
    with pytest.raises(ImportFailure):
        import_directory(batch, fresh, mode='demo')
    assert not fresh.exists()


def test_exact_midnight_deadline_survives_database_round_trip(batch, tmp_path):
    from datetime import datetime, timedelta
    from shared.models import Opportunity
    from shared.rules import application_state
    exact = '2026-11-12T00:00:00+09:00'
    edit(batch, 'opportunities', lambda rows: rows[0].update(application={'status':'open', 'closes_at':exact}))
    db = tmp_path / 'exact-deadline.db'
    import_directory(batch, db, mode='demo')
    with sqlite3.connect(db) as connection:
        payload = connection.execute("SELECT payload FROM opportunities WHERE id='synthetic-job'").fetchone()[0]
    restored = Opportunity.model_validate_json(payload)
    assert restored.application.closes_at.isoformat() == exact
    assert restored.application.closes_on is None
    midnight = datetime.fromisoformat(exact)
    assert application_state(restored.application, now=midnight-timedelta(microseconds=1)).status == 'open'
    assert application_state(restored.application, now=midnight).status == 'closed'
    assert import_directory(batch, db, mode='demo')['counts']['opportunities']['unchanged'] == 3
