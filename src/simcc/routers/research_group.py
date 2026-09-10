from uuid import UUID

from fastapi import APIRouter, Query

from simcc.core.dependencies import AsyncSession, Filters
from simcc.schemas.research_group import (
    ResearchGroup,
    ResearchGroupAreaCount,
    ResearchLine,
)
from simcc.services import research_group_service

router = APIRouter(tags=['Research Group'])


@router.get('/research_group', response_model=list[ResearchGroup])
async def list_research_groups(
    session: AsyncSession,
    filters: Filters,
):
    return await research_group_service.list_research_groups(session, filters)


@router.get('/research_group_lines', response_model=list[ResearchLine])
async def list_research_lines(
    session: AsyncSession,
    group_id: UUID = Query(...),
):
    return await research_group_service.list_research_lines(session, group_id)


@router.get(
    '/research_group/count', response_model=list[ResearchGroupAreaCount]
)
@router.get(
    '/research_group/chart', response_model=list[ResearchGroupAreaCount]
)
async def get_research_group_count(
    session: AsyncSession,
    filters: Filters,
):
    return await research_group_service.count_research_groups_by_area(
        session, filters
    )
