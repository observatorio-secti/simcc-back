from fastapi import APIRouter

from simcc.core.dependencies import (
    AsyncSession,
    CurrentUser,
    Filters,
)
from simcc.v1.schemas.production import ProfessionalExperience
from simcc.v1.services import production_service

router = APIRouter(tags=['Production - Professional Experience'])


@router.get(
    '/production/professional-experience',
    response_model=list[ProfessionalExperience],
)
@router.get('/professional_experience', include_in_schema=False)
async def list_professional_experience(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.star = current_user if filters.star else None

    return await production_service.list_professional_experience(
        session, filters
    )
