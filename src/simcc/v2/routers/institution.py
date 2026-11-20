"""Router do catálogo de instituições v2."""

import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from simcc.core.dependencies import AsyncSession
from simcc.v2.dependencies import PaginationDep
from simcc.v2.errors import ApiError
from simcc.v2.repositories import catalog_repo
from simcc.v2.schemas.catalog import (
    CatalogSort,
    InstitutionDetail,
    InstitutionFilter,
    InstitutionListResponse,
)
from simcc.v2.schemas.envelope import (
    ERROR_RESPONSES,
    LIST_ERROR_RESPONSES,
    DetailResponse,
)
from simcc.v2.schemas.params import PaginationParams, build_pagination
from simcc.v2.schemas.query import as_query, forbid_unknown_params
from simcc.v2.schemas.researcher import Sort
from simcc.v2.services.meta import build_meta

router = APIRouter(tags=['Institution v2'])


@router.get(
    '/institution',
    response_model=InstitutionListResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[
        Depends(
            forbid_unknown_params(
                InstitutionFilter, PaginationParams, CatalogSort
            )
        )
    ],
)
async def list_institutions(
    session: AsyncSession,
    pagination: PaginationDep,
    filters: Annotated[
        InstitutionFilter, Depends(as_query(InstitutionFilter))
    ],
    sort: Annotated[CatalogSort, Depends(as_query(CatalogSort))],
) -> InstitutionListResponse:
    """Retorna lista paginada de instituições cadastradas."""
    start = time.perf_counter()
    items, total_items = await catalog_repo.fetch_institutions(
        session=session, filters=filters, pagination=pagination, sort=sort
    )
    return InstitutionListResponse(
        data=items,
        pagination=build_pagination(pagination, total_items),
        filters_applied=filters,
        sort=Sort.model_validate(sort),
        meta=await build_meta(session, start),
    )


@router.get(
    '/institution/{institution_id}',
    response_model=DetailResponse[InstitutionDetail],
    responses=ERROR_RESPONSES,
)
async def get_institution(
    session: AsyncSession, institution_id: UUID
) -> DetailResponse[InstitutionDetail]:
    """Retorna o detalhe de uma instituição."""
    start = time.perf_counter()
    institution = await catalog_repo.fetch_institution(session, institution_id)
    if institution is None:
        raise ApiError(404, 'Instituição não encontrada.')
    return DetailResponse[InstitutionDetail](
        data=institution, meta=await build_meta(session, start)
    )
