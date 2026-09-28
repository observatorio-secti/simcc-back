from fastapi import APIRouter

from simcc.core.dependencies import (
    AsyncSession,
    CurrentUser,
    Filters,
)
from simcc.v1.schemas.production import (
    GuidanceProduction,
    ReportProduction,
    ResearchProjectProduction,
)
from simcc.v1.services import production_service

router = APIRouter(tags=['Production - Projects & Guidance'])


@router.get(
    '/production/research-project',
    response_model=list[ResearchProjectProduction],
)
@router.get('/researcher_research_project', include_in_schema=False)
async def list_research_project(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.star = current_user if filters.star else None

    return await production_service.list_research_projects(session, filters)


@router.get('/production/guidance', response_model=list[GuidanceProduction])
@router.get('/guidance_researcher', include_in_schema=False)
async def list_guidance(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.star = current_user if filters.star else None

    return await production_service.list_guidance_production(session, filters)


@router.get('/production/report', response_model=list[ReportProduction])
@router.get('/researcher_report', include_in_schema=False)
async def list_report(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.star = current_user if filters.star else None

    return await production_service.list_researcher_report(session, filters)
