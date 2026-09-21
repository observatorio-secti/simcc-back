# ruff: noqa: PLR0913, PLR0917
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from simcc.core.dependencies import AsyncSession
from simcc.v2.schemas.researcher import SearchResponse
from simcc.v2.services import researcher_service

router = APIRouter(tags=['Researcher v2'])


@router.get('/researcher', response_model=SearchResponse)
async def list_researchers(
    session: AsyncSession,
    q: Optional[str] = Query(
        None, description='Termo de busca pelo nome do pesquisador'
    ),
    year_start: Optional[int] = Query(None, description='Ano inicial'),
    year_end: Optional[int] = Query(None, description='Ano final'),
    institution_id: Optional[UUID] = Query(
        None, description='ID da Instituição'
    ),
    graduate_program_id: Optional[UUID] = Query(
        None, description='ID do Programa de Pós-Graduação'
    ),
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
