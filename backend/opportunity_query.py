"""Opportunity HTTP routes; storage and error formatting live independently."""
from collections.abc import Callable
from typing import Literal
from fastapi import APIRouter, Query
from backend.settings import Settings
from backend.catalog_store import CatalogUnavailable, read_catalog, read_opportunities
from backend.responses import error_response as query_error
from backend.opportunity_search import filter_opportunities
from shared.models import Opportunity, OpportunityType, Page


def create_opportunity_router(
    settings: Settings, *, enabled: Callable[[], bool] = lambda: True,
) -> APIRouter:
    """The main app supplies its reviewed capability gate."""
    router = APIRouter(prefix='/api/v1')

    @router.get('/opportunities', response_model=Page[Opportunity])
    def opportunities(limit: int = Query(default=20, ge=1, le=100),
                      offset: int = Query(default=0, ge=0),
                      q: str | None = Query(default=None, max_length=200),
                      types: list[OpportunityType] | None = Query(default=None),
                      publisher: Literal['school', 'official', 'aggregator', 'other'] | None = Query(default=None)):
        if not enabled():
            return query_error(503, 'FEATURE_UNAVAILABLE', '공고 조회 기능이 비활성 상태입니다.')
        try:
            snapshot = read_catalog(settings)
        except CatalogUnavailable:
            return query_error(503, 'FEATURE_UNAVAILABLE', '공고 자료를 조회할 수 없습니다.')
        candidates = snapshot['opportunities']
        if publisher is not None:
            source_ids = {source.id for source in snapshot['sources'] if source.kind == publisher}
            candidates = [item for item in candidates if source_ids.intersection(item.source_ids)]
        items = filter_opportunities(candidates, q=q, types=types)
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
