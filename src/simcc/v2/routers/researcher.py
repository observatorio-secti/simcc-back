"""Router para busca e listagem de pesquisadores v2."""

import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from fastapi.responses import FileResponse

from simcc.core.dependencies import AsyncSession
from simcc.v2.dependencies import (
    SearchCacheDep,
)
from simcc.v2.schemas.envelope import (
    ERROR_RESPONSES,
    LIST_ERROR_RESPONSES,
    DetailResponse,
)
from simcc.v2.schemas.filters import (
    ResearcherFilter,
    validate_unknown_researcher_params,
)
from simcc.v2.schemas.params import (
    PaginationParams,
    SearchOptions,
    SortParams,
)
from simcc.v2.schemas.query import as_query, forbid_unknown_params
from simcc.v2.schemas.researcher import (
    ResearcherDetail,
    ResearcherDetailOptions,
    SearchResponse,
)
from simcc.v2.services import researcher_service
from simcc.v2.services.meta import build_meta

router = APIRouter(tags=['Researcher v2'])


@router.get(
    '/researcher',
    response_model=SearchResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[Depends(validate_unknown_researcher_params)],
)
async def list_researchers(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    cache: SearchCacheDep,
    filters: Annotated[ResearcherFilter, Depends(as_query(ResearcherFilter))],
    pagination: Annotated[
        PaginationParams, Depends(as_query(PaginationParams))
    ],
    sort: Annotated[SortParams, Depends(as_query(SortParams))],
    options: Annotated[SearchOptions, Depends(as_query(SearchOptions))],
) -> SearchResponse:
    """Retorna lista paginada de pesquisadores com filtros e ordenação."""
    return await researcher_service.search_researchers(
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
        options=options,
        cache=cache,
    )


@router.get(
    '/researcher/{researcher_id}',
    response_model=DetailResponse[ResearcherDetail],
    responses=ERROR_RESPONSES,
    dependencies=[Depends(forbid_unknown_params(ResearcherDetailOptions))],
)
async def get_researcher(
    session: AsyncSession,
    researcher_id: Annotated[
        UUID | str,
        Path(description='ID (UUID) ou Lattes ID do pesquisador'),
    ],
    options: Annotated[
        ResearcherDetailOptions, Depends(as_query(ResearcherDetailOptions))
    ],
) -> DetailResponse[ResearcherDetail]:
    """Retorna o perfil de um pesquisador. Formação, experiência e fomento
    vêm com `include=education,experience,foment`."""
    start = time.perf_counter()
    researcher = await researcher_service.get_researcher(
        session=session,
        researcher_id=researcher_id,
        include=options.include,
    )
    return DetailResponse(
        data=researcher, meta=await build_meta(session, start)
    )


@router.get(
    '/researcher/{researcher_id}/image',
    response_class=FileResponse,
    responses=ERROR_RESPONSES,
)
async def get_researcher_image(
    session: AsyncSession,
    researcher_id: Annotated[
        UUID | str,
        Path(description='ID (UUID) ou Lattes ID do pesquisador'),
    ],
) -> FileResponse:
    """Retorna a foto do pesquisador."""
    path = await researcher_service.get_researcher_image_path(
        session=session, researcher_id=researcher_id
    )
    return FileResponse(path)
