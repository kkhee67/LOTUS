"""Caching the reference schema must never cache catalog validity or payloads."""
import json
import sqlite3
import pytest
from backend.catalog_store import CatalogUnavailable, read_catalog


def test_warm_schema_still_reads_changes_and_rejects_later_damage(real_catalog):
    db, settings = real_catalog
    first = read_catalog(settings)['opportunities'][0]
    with sqlite3.connect(db) as connection:
        payload, = connection.execute('SELECT payload FROM opportunities WHERE id=?', (first.id,)).fetchone()
        value = json.loads(payload)
        value['title'] = '검사 중 수정된 제목'
        connection.execute('UPDATE opportunities SET payload=? WHERE id=?', (json.dumps(value), first.id))
    assert read_catalog(settings)['opportunities'][0].title == '검사 중 수정된 제목'
    assert first.title != '검사 중 수정된 제목'
    with sqlite3.connect(db) as connection:
        connection.execute('ALTER TABLE opportunities ADD COLUMN unsupported TEXT')
    before = db.read_bytes()
    with pytest.raises(CatalogUnavailable):
        read_catalog(settings)
    assert db.read_bytes() == before
