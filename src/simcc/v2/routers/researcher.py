# ruff: noqa: PLR0913, PLR0917
from fastapi import APIRouter, Depends, Query

from simcc.core.dependencies import AsyncSession
from simcc.v2.schemas.filters import ResearcherFilter
from simcc.v2.schemas.researcher import SearchResponse
from simcc.v2.services import researcher_service

router = APIRouter(tags=['Researcher v2'])


@router.get('/researcher', response_model=SearchResponse)
async def list_researchers(
    session: AsyncSession,
    filters: ResearcherFilter = Depends(),
    page: int = Query(1, ge=1, description='Número da página'),
    per_page: int = Query(20, ge=1, le=100, description='Itens por página'),
    sort_by: str = Query('name', description='Campo para ordenação'),
    sort_order: str = Query(
        'asc',
        pattern='^(asc|desc)$',
        description='Direção da ordenação (asc/desc)',
    ),
) -> SearchResponse:
    return await researcher_service.search_researchers(
        session=session,
        filters=filters,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
    )
