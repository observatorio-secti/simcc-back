"""Router para catálogo de instituições v2."""

import math
from typing import Optional

from fastapi import APIRouter, Query

from simcc.core.dependencies import AsyncSession
from simcc.v2.dependencies import PaginationDep
from simcc.v2.repositories import catalog_repo
from simcc.v2.schemas.institution import InstitutionListResponse
from simcc.v2.schemas.params import Pagination

router = APIRouter(tags=['Institution v2'])


@router.get('/institution', response_model=InstitutionListResponse)
async def list_institutions(
    session: AsyncSession,
    pagination: PaginationDep,
    q: Optional[str] = Query(
        None, description='Termo para busca por nome ou sigla'
    ),
) -> InstitutionListResponse:
    """Retorna lista paginada de instituições cadastradas."""
    items, total_items = await catalog_repo.fetch_institutions(
        session=session,
        q=q,
        pagination=pagination,
    )
    if total_items == 0:
        total_pages = 0
        has_next = False
        has_prev = False
    else:
        total_pages = (
            math.ceil(total_items / pagination.per_page)
            if pagination.per_page > 0
            else 0
        )
        has_next = pagination.page < total_pages
        has_prev = pagination.page > 1 and pagination.page <= total_pages + 1

    return InstitutionListResponse(
        data=items,
        pagination=Pagination(
            page=pagination.page,
            per_page=pagination.per_page,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        ),
    )
