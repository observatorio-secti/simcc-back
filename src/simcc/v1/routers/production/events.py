from fastapi import APIRouter

from simcc.core.dependencies import (
    AsyncSession,
    Filters,
)
from simcc.v1.schemas.production import (
    EventProduction,
    ParticipationEventProduction,
)
from simcc.v1.services import production_service

router = APIRouter(tags=['Production - Events'])


@router.get('/production/event/article', response_model=list[EventProduction])
@router.get('/researcher_production/events', include_in_schema=False)
async def list_event_article(
    session: AsyncSession,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term

    return await production_service.list_researcher_production_events(
        session, filters
    )


@router.get(
    '/production/event/participation',
    response_model=list[ParticipationEventProduction],
)
@router.get('/pevent_researcher', include_in_schema=False)
async def list_event_participation(
    session: AsyncSession,
    filters: Filters,
    terms: str | None = None,
    nature: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.type = nature if nature else filters.type

    return await production_service.list_participation_event(session, filters)
