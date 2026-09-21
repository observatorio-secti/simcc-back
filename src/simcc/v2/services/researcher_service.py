# ruff: noqa: PLR0913, PLR0917
import math
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.repositories import researcher_repo
from simcc.v2.schemas.researcher import (
    FiltersApplied,
    Meta,
    Pagination,
    Researcher,
    SearchResponse,
    Sort,
)


async def search_researchers(
    session: AsyncSession,
    q: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    institution_id: Optional[UUID] = None,
    graduate_program_id: Optional[UUID] = None,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = 'name',
    sort_order: str = 'asc',
) -> SearchResponse:
    start_time = time.perf_counter()

    items, total_items = await researcher_repo.fetch_researchers(
        session=session,
        q=q,
        year_start=year_start,
        year_end=year_end,
        institution_id=institution_id,
        graduate_program_id=graduate_program_id,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    took_ms = max(1, int((time.perf_counter() - start_time) * 1000))
    total_pages = math.ceil(total_items / per_page) if per_page > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1 and total_pages > 0

    return SearchResponse(
        data=[
            Researcher(researcher_id=item['researcher_id'], name=item['name'])
            for item in items
        ],
        pagination=Pagination(
            page=page,
            per_page=per_page,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        ),
        filters_applied=FiltersApplied(
            q=q,
            year_start=year_start,
            year_end=year_end,
            institution_id=institution_id,
            graduate_program_id=graduate_program_id,
        ),
        sort=Sort(by=sort_by, order=sort_order),
        meta=Meta(
            took_ms=took_ms,
            cached=False,
            timestamp=datetime.now(timezone.utc),
        ),
        facets=None,
        summary=None,
    )
