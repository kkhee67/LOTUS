"""Validated, atomic imports of public catalog data. No profile storage."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Literal

from pydantic import TypeAdapter, ValidationError
from backend.settings import Settings
# Compatibility names remain available to existing importer callers.
from backend.catalog_schema import (
    MODE_KIND, MODELS, SCHEMA_VERSION, ImportFailure, unique_json_object as _unique_object,
    create_schema as _create_schema, validate_schema as _validate_schema,
    validate_stored_payload, database_path,
)
from shared.validation import validate_dataset

def load_dataset(directory: Path, *, mode: str) -> dict:
    if mode not in MODE_KIND:
        raise ImportFailure('mode는 demo 또는 real이어야 합니다.')
    dataset = {}
    for table, model in MODELS.items():
        try:
            value = json.loads((directory / f'{table}.json').read_text(encoding='utf-8'),
                               object_pairs_hook=_unique_object)
            dataset[table] = TypeAdapter(list[model]).validate_python(value)
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            raise ImportFailure(f'{table}.json 읽기 또는 공통 모델 검증 실패.') from exc
    try:
        validate_dataset(**dataset)
    except ValueError as exc:
        raise ImportFailure('입력 자료의 ID·출처·분야 코드 또는 자료 종류 검증 실패.') from exc
    if any(item.source_kind != MODE_KIND[mode] for rows in dataset.values() for item in rows):
        raise ImportFailure('입력 자료 종류와 mode가 일치하지 않습니다.')
    return dataset


def _schema(connection: sqlite3.Connection, mode: str) -> None:
    version = connection.execute('PRAGMA user_version').fetchone()[0]
    if version not in (0, SCHEMA_VERSION):
        raise ImportFailure('지원하지 않는 DB 스키마 버전입니다. 마이그레이션 검토가 필요합니다.')
    if version == 0:
        if connection.execute("SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchone():
            raise ImportFailure('관리되지 않는 기존 DB입니다. 자동으로 변경하지 않습니다.')
        _create_schema(connection, mode)
    _validate_schema(connection)
    row = connection.execute('SELECT mode FROM import_metadata WHERE id=1').fetchone()
    if row is None or row[0] != mode:
        raise ImportFailure('DB의 자료 모드와 일치하지 않습니다. real/demo는 별도 DB를 사용하세요.')


def _canonical(item) -> str:
    return json.dumps(item.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def import_directory(directory: Path, database: Path, *, mode: Literal['demo', 'real']) -> dict:
    """Validate all four files before opening DB, then apply one transaction.

    Each batch includes every source it references. Omitted DB items remain.
    Existing and incoming data are checked together before any upsert.
    Older records are ignored and counted as unchanged. Equal timestamps allow corrections.
    """
    dataset = load_dataset(Path(directory), mode=mode)
    database = Path(database)
    connection = None
    try:
        database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database, timeout=5, isolation_level=None)
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('BEGIN IMMEDIATE')
        _schema(connection, mode)
        counts = {}
        merged = {}
        writes = {}
        for table, model in MODELS.items():
            stored = list(connection.execute(f'SELECT id, source_kind, payload FROM {table}'))
            existing = {key: payload for key, kind, payload in stored}
            if any(kind != MODE_KIND[mode] for key, kind, payload in stored):
                raise ImportFailure('기존 DB 자료 종류 열과 mode가 일치하지 않습니다.')
            parsed = {key: validate_stored_payload(model, value) for key, value in existing.items()}
            if any(key != item.id or item.source_kind != MODE_KIND[mode] for key, item in parsed.items()):
                raise ImportFailure('기존 DB 자료와 ID 또는 mode가 일치하지 않습니다.')
            if table != 'sources':
                expected_links = {(item.id, source_id) for item in parsed.values()
                                  for source_id in item.source_ids}
                actual_links = set(connection.execute(f'SELECT item_id, source_id FROM {table}_sources'))
                if actual_links != expected_links:
                    raise ImportFailure('기존 DB의 출처 연결과 원본이 일치하지 않습니다. 복구 검토가 필요합니다.')
            stats = counts[table] = {'inserted': 0, 'updated': 0, 'unchanged': 0}
            writes[table] = []
            for item in dataset[table]:
                previous = parsed.get(item.id)
                if previous is not None and item.checked_at < previous.checked_at:
                    stats['unchanged'] += 1
                    continue
                payload = _canonical(item)
                if payload == existing.get(item.id):
                    stats['unchanged'] += 1
                    continue
                stats['inserted' if previous is None else 'updated'] += 1
                parsed[item.id] = item
                writes[table].append((item, payload))
            merged[table] = list(parsed.values())
        validate_dataset(**merged)
        for table, rows in writes.items():
            for item, payload in rows:
                connection.execute(f'''INSERT INTO {table} (id, source_kind, payload) VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET source_kind=excluded.source_kind, payload=excluded.payload''',
                                   (item.id, item.source_kind, payload))
                if table != 'sources':
                    connection.execute(f'DELETE FROM {table}_sources WHERE item_id=?', (item.id,))
                    connection.executemany(f'INSERT INTO {table}_sources (item_id, source_id) VALUES (?, ?)',
                                           [(item.id, source_id) for source_id in sorted(set(item.source_ids))])
        connection.commit()
        return {'schema_version': SCHEMA_VERSION, 'mode': mode, 'counts': counts}
    except (OSError, sqlite3.Error, ValueError) as exc:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        if isinstance(exc, ImportFailure):
            raise
        raise ImportFailure('DB 또는 자료 검증 오류로 입력을 취소했습니다. 기존 자료는 보존됩니다.') from exc
    finally:
        if connection is not None:
            connection.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='검증된 공공 자료 JSON 배열 네 개를 SQLite에 입력합니다.')
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--database', type=Path, help='생략하면 DATABASE_URL 설정 사용')
    parser.add_argument('--mode', choices=list(MODE_KIND), help='생략하면 DATA_MODE 설정 사용')
    args = parser.parse_args(argv)
    try:
        settings = Settings()
        database = args.database if args.database is not None else database_path(settings.database_url)
        result = import_directory(args.input_dir, database, mode=args.mode or settings.data_mode)
    except ValidationError:
        print(json.dumps({'error': {'code': 'IMPORT_FAILED', 'message': '환경 설정 검증 실패.', 'details': []}}, ensure_ascii=False), file=sys.stderr)
        return 1
    except ImportFailure as exc:
        print(json.dumps({'error': {'code': 'IMPORT_FAILED', 'message': str(exc), 'details': []}}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
