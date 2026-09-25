"""Router para busca e listagem de pesquisadores v2."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from simcc.core.dependencies import AsyncSession
from simcc.v2.schemas.filters import (
    ResearcherFilter,
    get_researcher_filter,
    validate_unknown_researcher_params,
)
from simcc.v2.schemas.params import (
    PaginationParams,
    SearchOptions,
    SortParams,
    get_search_options,
)
from simcc.v2.schemas.researcher import ResearcherDetail, SearchResponse
from simcc.v2.services import researcher_service

router = APIRouter(tags=['Researcher v2'])


@router.get(
    '/researcher',
    response_model=SearchResponse,
    dependencies=[Depends(validate_unknown_researcher_params)],
)
async def list_researchers(
    session: AsyncSession,
    filters: ResearcherFilter = Depends(get_researcher_filter),
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    options: SearchOptions = Depends(get_search_options),
) -> SearchResponse:
    """Retorna lista paginada de pesquisadores com filtros e ordenação."""
    return await researcher_service.search_researchers(
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
        options=options,
    )


@router.get('/researcher/{researcher_id}', response_model=ResearcherDetail)
async def get_researcher(
    session: AsyncSession,
    researcher_id: UUID,
) -> ResearcherDetail:
    """Retorna o perfil completo de um pesquisador."""
    return await researcher_service.get_researcher(
        session=session, researcher_id=researcher_id
    )


@router.get('/researcher/{researcher_id}/image', response_class=FileResponse)
async def get_researcher_image(
    session: AsyncSession,
    researcher_id: UUID,
) -> FileResponse:
    """Retorna a foto do pesquisador."""
    path = await researcher_service.get_researcher_image_path(
        session=session, researcher_id=researcher_id
    )
    return FileResponse(path)
