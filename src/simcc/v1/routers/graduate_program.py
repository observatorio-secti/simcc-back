from uuid import UUID

from fastapi import APIRouter, Query

from simcc.core.dependencies import AsyncSession, Filters
from simcc.v1.schemas.external import ResearcherArticleProduction
from simcc.v1.schemas.graduate_program import (
    GraduateProgram,
    GraduateProgramResearcher,
    ResearchLine,
)
from simcc.v1.services import graduate_program_service

router = APIRouter(tags=['Graduate Program'])


@router.get('/graduate_program', response_model=list[GraduateProgram])
@router.get(
    '/graduate_program_profnit',
    response_model=list[GraduateProgram],
    include_in_schema=False,
)
async def list_graduate_programs(
    session: AsyncSession,
    filters: Filters,
    id: UUID | str = Query(None),
):
    filters.graduate_program_id = id if id else None
    return await graduate_program_service.list_graduate_programs(
        session, filters
    )


@router.get('/graduate_program/lines', response_model=list[ResearchLine])
async def list_research_lines(
    session: AsyncSession,
    filters: Filters,
):
    return await graduate_program_service.list_research_lines(session, filters)


@router.get(
    '/graduate_program/{program_id}/article_production',
    response_model=list[ResearcherArticleProduction],
)
async def list_article_production(
    session: AsyncSession,
    program_id: UUID,
    year: int = Query(2020),
):
    return await graduate_program_service.list_article_production(
        session, program_id, year
    )


@router.get(
    '/graduate_program_researcher',
    response_model=list[GraduateProgramResearcher],
)
async def list_graduate_program_researchers(
    session: AsyncSession,
    filters: Filters,
):
    return await graduate_program_service.list_graduate_program_researchers(
        session, filters
    )
