import math
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.repositories.researcher_repo import (
    fetch_matched_in_v2,
    fetch_researchers_v2,
)
from simcc.v2.schemas.envelope import (
    PaginationMetadata,
    ResponseEnvelope,
    ResponseMeta,
    SortMetadata,
)
from simcc.v2.schemas.researcher import MatchedInItem, ResearcherV2


def build_response_envelope(
    data: list[Any],
    total_items: int,
    query_params: dict[str, Any],
    start_time: float,
    cached: bool = False,
) -> ResponseEnvelope:
    pagination = query_params.get('pagination', {})
    filters_applied = query_params.get('filters', {})
    sort = query_params.get('sort', {})

    page = pagination.get('page', 1)
    per_page = pagination.get('per_page', 20)
    total_pages = math.ceil(total_items / per_page) if per_page > 0 else 0
    took_ms = max(1, int((time.perf_counter() - start_time) * 1000))

    return ResponseEnvelope(
        data=data,
        pagination=PaginationMetadata(
            page=page,
            per_page=per_page,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1 and total_pages > 0,
        ),
        filters_applied=filters_applied,
        sort=SortMetadata(
            by=sort.get('by', 'name'),
            order=sort.get('order', 'asc'),
        ),
        meta=ResponseMeta(
            took_ms=took_ms,
            cached=cached,
            timestamp=datetime.now(timezone.utc),
        ),
    )


async def _resolve_embedding_vector(
    embeddings_provider: Any, q: str | None
) -> list[float] | None:
    if not q or embeddings_provider is None:
        return None
    try:
        return await embeddings_provider.get_embeddings(q)
    except Exception:
        return None


def _map_researchers(
    records: list[dict[str, Any]],
    matched_map: dict[str, list[dict[str, Any]]],
    has_q: bool,
) -> list[ResearcherV2]:
    data = []
    for r in records:
        rid = r.get('researcher_id')
        matched_items = None
        if has_q and rid and rid in matched_map:
            matched_items = [
                MatchedInItem(**item) for item in matched_map[rid]
            ]

        data.append(
            ResearcherV2(
                researcher_id=rid,
                name=r['name'],
                relevance_score=r.get('relevance_score'),
                matched_in=matched_items,
            )
        )
    return data


async def list_researchers(
    session: AsyncSession,
    query_params: dict[str, Any],
    embeddings_provider: Any = None,
    cosine_threshold: float = 0.65,
) -> ResponseEnvelope[ResearcherV2]:
    start_time = time.perf_counter()
    filters = query_params.get('filters', {})
    q = filters.get('q')

    embedding_vector = await _resolve_embedding_vector(embeddings_provider, q)

    # Fase 1: Busca e paginação (Camada 2)
    records, total_items = await fetch_researchers_v2(
        session=session,
        query_params=query_params,
        embedding_vector=embedding_vector,
        cosine_threshold=cosine_threshold,
    )

    # Fase 2: Resolução de evidências matched_in (Camada 1)
    matched_map: dict[str, list[dict[str, Any]]] = {}
    if q and records:
        r_ids = [r['researcher_id'] for r in records if r.get('researcher_id')]
        matched_map = await fetch_matched_in_v2(
            session=session,
            researcher_ids=r_ids,
            search_term=q,
        )

    data = _map_researchers(records, matched_map, has_q=bool(q))

    return build_response_envelope(
        data=data,
        total_items=total_items,
        query_params=query_params,
        start_time=start_time,
        cached=False,
    )
