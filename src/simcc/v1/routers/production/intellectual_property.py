from fastapi import APIRouter

from simcc.core.dependencies import (
    AsyncSession,
    CurrentUser,
    Filters,
)
from simcc.v1.schemas.production import (
    BrandProduction,
    PatentProduction,
    SoftwareProduction,
)
from simcc.v1.services import production_service

router = APIRouter(tags=['Production - Intellectual Property'])


@router.get('/production/patent', response_model=list[PatentProduction])
@router.get('/patent_production_researcher', include_in_schema=False)
async def list_patent(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.star = current_user if filters.star else None

    return await production_service.list_patent(session, filters)


@router.get('/production/brand', response_model=list[BrandProduction])
@router.get('/brand_production_researcher', include_in_schema=False)
async def list_brand(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.star = current_user if filters.star else None

    return await production_service.list_brand(session, filters)


@router.get('/production/software', response_model=list[SoftwareProduction])
@router.get('/software_production_researcher', include_in_schema=False)
async def list_software(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.star = current_user if filters.star else None

    return await production_service.list_software(session, filters)
