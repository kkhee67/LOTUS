"""Read-only catalog snapshots, shared by routes and preflight checks."""
from contextlib import closing
import sqlite3
from backend.catalog_schema import (
    MODELS, MODE_KIND, SCHEMA_VERSION, validate_schema, database_path, validate_stored_payload,
)
from backend.settings import Settings
from shared.models import Opportunity
from shared.validation import validate_dataset


class CatalogUnavailable(ValueError):
    """Public-safe failure; never contains DB paths or stored payloads."""


def read_catalog(settings: Settings) -> dict:
    """Read and validate one consistent importer snapshot without creating a DB."""
    try:
        path = database_path(settings.database_url).resolve()
        # Convert the validated file path to an escaped URI before adding mode=ro.
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
            db.execute('PRAGMA query_only=ON')
            db.execute('BEGIN')
            if db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
                raise CatalogUnavailable('공고 자료를 조회할 수 없습니다.')
            validate_schema(db)
            mode = db.execute('SELECT mode FROM import_metadata WHERE id=1').fetchone()
            if mode != (settings.data_mode,):
                raise CatalogUnavailable('공고 자료를 조회할 수 없습니다.')
            dataset = {}
            for table, model in MODELS.items():
                rows = db.execute(f'SELECT id, source_kind, payload FROM {table}').fetchall()
                items = [validate_stored_payload(model, payload) for _, _, payload in rows]
                if any(key != item.id or kind != MODE_KIND[settings.data_mode]
                       or item.source_kind != kind
                       for (key, kind, _), item in zip(rows, items)):
                    raise CatalogUnavailable('공고 자료를 조회할 수 없습니다.')
                if table != 'sources':
                    expected = {(item.id, source_id) for item in items for source_id in item.source_ids}
                    actual = set(db.execute(f'SELECT item_id, source_id FROM {table}_sources'))
                    if actual != expected:
                        raise CatalogUnavailable('공고 자료를 조회할 수 없습니다.')
                dataset[table] = items
            validate_dataset(**dataset)
            return {table: sorted(items, key=lambda item: item.id)
                    for table, items in dataset.items()}
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise CatalogUnavailable('공고 자료를 조회할 수 없습니다.') from exc


def read_opportunities(settings: Settings) -> list[Opportunity]:
    return read_catalog(settings)['opportunities']
