"""Read-only, validated opportunity list/detail routes."""
from contextlib import closing
from collections.abc import Callable
import sqlite3

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.importer import (
    MODELS, MODE_KIND, SCHEMA_VERSION, _validate_schema, database_path, validate_stored_payload,
)
from backend.settings import Settings
from shared.models import ErrorBody, ErrorResponse, Opportunity, Page
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
            _validate_schema(db)
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


def query_error(status: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status, content=body.model_dump(mode='json'))


def create_opportunity_router(
    settings: Settings, *, enabled: Callable[[], bool] = lambda: True,
) -> APIRouter:
    """The main app supplies its reviewed capability gate."""
    router = APIRouter(prefix='/api/v1')

    @router.get('/opportunities', response_model=Page[Opportunity])
    def opportunities(limit: int = Query(default=20, ge=1, le=100),
                      offset: int = Query(default=0, ge=0)):
        if not enabled():
            return query_error(503, 'FEATURE_UNAVAILABLE', '공고 조회 기능이 비활성 상태입니다.')
        try:
            items = read_opportunities(settings)
        except CatalogUnavailable:
            return query_error(503, 'FEATURE_UNAVAILABLE', '공고 자료를 조회할 수 없습니다.')
        return Page[Opportunity](items=items[offset:offset + limit], total=len(items),
                                 limit=limit, offset=offset)

    @router.get('/opportunities/{id}', response_model=Opportunity)
    def opportunity(id: str):
        if not enabled():
            return query_error(503, 'FEATURE_UNAVAILABLE', '공고 조회 기능이 비활성 상태입니다.')
        try:
            items = read_opportunities(settings)
        except CatalogUnavailable:
            return query_error(503, 'FEATURE_UNAVAILABLE', '공고 자료를 조회할 수 없습니다.')
        for item in items:
            if item.id == id:
                return item
        return query_error(404, 'NOT_FOUND', '공고를 찾을 수 없습니다.')

    return router
