"""Router do catálogo de programas de pós-graduação v2.

O caminho oficial é `/graduate-program`; `/graduate_program` continua
aceito como alias, fora do OpenAPI.
"""

import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from simcc.core.dependencies import AsyncSession
from simcc.v2.dependencies import PaginationDep
from simcc.v2.errors import ApiError
from simcc.v2.repositories import catalog_repo
from simcc.v2.schemas.catalog import (
    CatalogResponse,
    CatalogSort,
    GraduateProgramDetail,
    GraduateProgramFilter,
    GraduateProgramOptions,
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

router = APIRouter(tags=['Graduate Program v2'])

_LIST_DEPENDENCIES = [
    Depends(
        forbid_unknown_params(
            GraduateProgramFilter,
            PaginationParams,
            CatalogSort,
            GraduateProgramOptions,
        )
    )
]


async def list_graduate_programs(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    pagination: PaginationDep,
    filters: Annotated[
        GraduateProgramFilter, Depends(as_query(GraduateProgramFilter))
    ],
    sort: Annotated[CatalogSort, Depends(as_query(CatalogSort))],
    options: Annotated[
        GraduateProgramOptions, Depends(as_query(GraduateProgramOptions))
    ],
) -> CatalogResponse:
    """Retorna lista paginada de programas de pós-graduação."""
    start = time.perf_counter()
    items, total_items = await catalog_repo.fetch_graduate_programs(
        session=session, filters=filters, pagination=pagination, sort=sort
    )
    facets = None
    if options.facets:
        facets = await catalog_repo.fetch_graduate_program_facets(
            session, filters, options.facets, options.facet_limit
        )
    return CatalogResponse(
        data=items,
        pagination=build_pagination(pagination, total_items),
        filters_applied=filters,
        sort=Sort.model_validate(sort),
        meta=await build_meta(session, start),
        facets=facets,
    )


async def get_graduate_program(
    session: AsyncSession, program_id: UUID
) -> DetailResponse[GraduateProgramDetail]:
    """Retorna o detalhe do programa com suas linhas de pesquisa."""
    start = time.perf_counter()
    program = await catalog_repo.fetch_graduate_program(session, program_id)
    if program is None:
        raise ApiError(404, 'Programa de pós-graduação não encontrado.')
    return DetailResponse[GraduateProgramDetail](
        data=program, meta=await build_meta(session, start)
    )


for _path, _in_schema in (
    ('/graduate-program', True),
    ('/graduate_program', False),
):
    router.add_api_route(
        _path,
        list_graduate_programs,
        methods=['GET'],
        response_model=CatalogResponse,
        responses=LIST_ERROR_RESPONSES,
        dependencies=_LIST_DEPENDENCIES,
        include_in_schema=_in_schema,
    )
    router.add_api_route(
        f'{_path}/{{program_id}}',
        get_graduate_program,
        methods=['GET'],
        response_model=DetailResponse[GraduateProgramDetail],
        responses=ERROR_RESPONSES,
        include_in_schema=_in_schema,
    )
