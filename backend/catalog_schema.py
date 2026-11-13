"""Shared SQLite schema and payload rules; no CLI or HTTP dependencies."""
import json
import sqlite3
from pathlib import Path
from functools import lru_cache
from backend.settings import ROOT
from shared.models import Opportunity, ResourceLink, RoleProfile, Source

MODE_KIND = {'demo': 'synthetic', 'real': 'real'}
MODELS = {'sources': Source, 'opportunities': Opportunity,
          'roles': RoleProfile, 'resource_links': ResourceLink}
SCHEMA_VERSION = 1


class ImportFailure(ValueError):
    """A safe diagnostic: never includes source content or credentials."""


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ImportFailure('JSON 객체의 중복 키를 제거하세요.')
        result[key] = value
    return result


def validate_stored_payload(model, payload: str):
    """Use the same duplicate-key check for stored rows as for input files."""
    try:
        value = json.loads(payload, object_pairs_hook=unique_json_object)
    except RecursionError as exc:
        raise ImportFailure('기존 DB 자료의 JSON 구조를 확인해 주세요.') from exc
    return model.model_validate(value)


def create_schema(connection: sqlite3.Connection, mode: str) -> None:
    connection.execute("CREATE TABLE import_metadata (id INTEGER PRIMARY KEY CHECK(id=1), mode TEXT NOT NULL CHECK(mode IN ('demo','real')))")
    connection.execute('INSERT INTO import_metadata VALUES (1, ?)', (mode,))
    for table in MODELS:  # table names are fixed constants, never user input
        connection.execute(f'''CREATE TABLE {table} (
            id TEXT PRIMARY KEY NOT NULL,
            source_kind TEXT NOT NULL CHECK(source_kind IN ('real','synthetic')),
            payload TEXT NOT NULL CHECK(json_valid(payload)))''')
        if table != 'sources':
            connection.execute(f'''CREATE TABLE {table}_sources (
                item_id TEXT NOT NULL REFERENCES {table}(id) ON DELETE CASCADE,
                source_id TEXT NOT NULL REFERENCES sources(id),
                PRIMARY KEY(item_id, source_id))''')
    connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')


def validate_schema(connection: sqlite3.Connection) -> None:
    # Only the importer-created v1 table definitions are supported. Compare to a
    # immutable reference definition; never repair/migrate an unknown schema.
    def tables(db):
        return {name: ' '.join(sql.split()).lower() for name, sql in db.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}

    if tables(connection) != dict(_reference_tables()):
        raise ImportFailure('지원하지 않는 DB 테이블 구조입니다. 마이그레이션 검토가 필요합니다.')
    if connection.execute('PRAGMA foreign_key_check').fetchone():
        raise ImportFailure('기존 DB의 출처 참조가 손상되었습니다. 복구 검토가 필요합니다.')


def database_path(url: str) -> Path:
    prefix = 'sqlite:///'
    if not url.startswith(prefix):
        raise ImportFailure('DATABASE_URL은 sqlite:/// 파일 경로만 지원합니다.')
    value = url[len(prefix):]
    if not value or value == ':memory:' or '?' in value or '#' in value:
        raise ImportFailure('유효한 SQLite 파일 경로가 필요합니다.')
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


@lru_cache(maxsize=1)
def _reference_tables() -> tuple[tuple[str, str], ...]:
    """Only cache immutable schema definitions, never database contents or validity."""
    reference = sqlite3.connect(':memory:')
    try:
        create_schema(reference, 'demo')
        return tuple((name, ' '.join(sql.split()).lower()) for name, sql in reference.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
    finally:
        reference.close()
