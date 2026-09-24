from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query

from simcc.core.dependencies import AsyncSession, Filters
from simcc.v1.schemas.production import (
    GeneralProductionMetrics,
    GraduateProgramProduction,
)
from simcc.v1.services import production_service

router = APIRouter(tags=['Production - Summaries'])


@router.get(
    '/production/graduate-program',
    response_model=list[GraduateProgramProduction],
)
@router.get('/graduate_program_production', include_in_schema=False)
async def get_graduate_program_production(
    session: AsyncSession,
    filters: Filters,
    graduate_program_id: str | None = Query(None),
    year: int = Query(0),
    dep_id: str | None = Query(None),
):
    if graduate_program_id:
        filters.graduate_program_id = graduate_program_id
    if year:
        filters.year = year
    if dep_id:
        filters.dep_id = dep_id

    return await production_service.get_graduate_program_production(
        session, filters
    )


@router.get(
    '/production/general-data',
    response_model=list[GeneralProductionMetrics],
)
@router.get(
    '/ResearcherData/DadosGerais',
    include_in_schema=False,
    response_model=list[GeneralProductionMetrics],
)
@router.get(
    '/researcher/DadosGerais',
    include_in_schema=False,
    response_model=list[GeneralProductionMetrics],
)
async def get_general_production_metrics(
    session: AsyncSession,
    filters: Filters,
    year: int = Query(datetime.now().year - 10),
    graduate_program_id: UUID | None = Query(None),
    dep_id: str | None = Query(None),
    researcher_id: UUID | None = Query(None),
):
    filters.year = year
    if graduate_program_id:
        filters.graduate_program_id = graduate_program_id
    if dep_id:
        filters.dep_id = dep_id
    if researcher_id:
        filters.researcher_id = researcher_id

    return await production_service.list_general_production_metrics(
        session, filters
    )
