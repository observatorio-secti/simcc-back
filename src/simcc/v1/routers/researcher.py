import os
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from simcc.core.dependencies import AsyncSession, CurrentUser, Filters
from simcc.v1.schemas import DefaultFilters
from simcc.v1.schemas.researcher import (
    CoAuthorship,
    Lab,
    OriginalWord,
    Researcher,
    ResearcherScholarship,
    ResearcherTerm,
)
from simcc.v1.schemas.researcher_filter import ResearcherFilter
from simcc.v1.services import production_service, researcher_service

router = APIRouter(tags=['Researcher'])


@router.get(
    '/researcher/co-authorship/{researcher_id}',
    response_model=list[CoAuthorship],
)
async def list_co_authorship(
    session: AsyncSession,
    researcher_id: UUID,
):
    return await researcher_service.list_co_authorship(session, researcher_id)


@router.get(
    '/researcher/scholarship', response_model=list[ResearcherScholarship]
)
@router.get('/foment', include_in_schema=False)
async def list_scholarships(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    institution_id: UUID | None = Query(None),
):
    if institution_id:
        filters.institution_id = institution_id

    filters.star = current_user if filters.star else None
    return await production_service.list_researcher_scholarships(
        session, filters
    )


@router.get('/researcher/terms', response_model=list[ResearcherTerm])
@router.get('/lists_word_researcher', include_in_schema=False)
async def list_researcher_terms(
    session: AsyncSession,
    filters: Filters,
):
    return await researcher_service.list_researcher_terms(session, filters)


@router.get('/researchers/original-words', response_model=list[OriginalWord])
@router.get('/originals_words', include_in_schema=False)
async def list_original_words(
    session: AsyncSession,
    initials: str = Query(...),
    type: str = Query(...),
):
    return await researcher_service.list_original_words(
        session, initials, type
    )


@router.get(
    '/researchers/participation-events', response_model=list[Researcher]
)
@router.get('/researcherParticipationEvent', include_in_schema=False)
async def search_participation_event(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
):
    filters.star = current_user if filters.star else None
    return await researcher_service.search_researchers(
        session, filters, search_type='PARTICIPATION_EVENT', pagination=filters
    )


@router.get('/researchers/area-specialty', response_model=list[Researcher])
@router.get('/researcherArea_specialty', include_in_schema=False)
async def search_area_specialty(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    area_specialty: str | None = Query(None),
):
    filters.star = current_user if filters.star else None
    if area_specialty:
        filters.term = area_specialty

    return await researcher_service.search_researchers(
        session, filters, search_type='AREA_SPECIALTY', pagination=filters
    )


@router.get('/researchers/books', response_model=list[Researcher])
@router.get('/researcherBook', include_in_schema=False)
async def search_book_production(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
):
    filters.star = current_user if filters.star else None
    return await researcher_service.search_researchers(
        session, filters, search_type='BOOK', pagination=filters
    )


@router.get('/researchers', response_model=list[Researcher])
@router.get('/researcher', include_in_schema=False)
async def search_researcher(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    name: str | None = Query(None),
):
    filters.star = current_user if filters.star else None

    # Handle the duplicate logic for ARTICLE vs ABSTRACT
    search_type = 'ABSTRACT'
    if filters.type == 'ARTICLE':
        search_type = 'ARTICLE'

    return await researcher_service.search_researchers(
        session,
        filters,
        search_type=search_type,
        name=name,
        pagination=filters,
    )


@router.get('/researchers/foment', response_model=list[Researcher])
@router.get('/researcher/foment', include_in_schema=False)
async def search_foment(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
):
    filters.star = current_user if filters.star else None
    return await researcher_service.search_researchers(
        session, filters, search_type='FOMENT', pagination=filters
    )


@router.get(
    '/researcherName', include_in_schema=False, response_model=list[Researcher]
)
async def search_researcher_name(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    name: str | None = Query(None),
):
    filters.star = current_user if filters.star else None
    return await researcher_service.search_researchers(
        session, filters, search_type='ABSTRACT', name=name, pagination=filters
    )


@router.get('/researchers/outstanding', response_model=list[Researcher])
@router.get('/outstanding_researchers', include_in_schema=False)
async def search_outstanding(
    session: AsyncSession,
):
    return await researcher_service.get_outstanding_researchers(session)


@router.get('/researchers/patents', response_model=list[Researcher])
@router.get('/researcherPatent', include_in_schema=False)
async def search_patent(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
):
    filters.star = current_user if filters.star else None
    return await researcher_service.search_researchers(
        session, filters, search_type='PATENT', pagination=filters
    )


@router.get('/labs', response_model=list[Lab])
async def get_labs(
    session: AsyncSession,
    lattes_id: str | None = Query(None),
    researcher_id: UUID | str | None = Query(None),
):
    return await researcher_service.list_labs(
        session, lattes_id=lattes_id, researcher_id=researcher_id
    )


@router.get('/researchers/by-city', response_model=list[Researcher])
@router.get('/ResearcherData/ByCity', include_in_schema=False)
async def search_by_city(
    session: AsyncSession,
    city: str | None = Query(None),
):
    filters = DefaultFilters(city=city)
    return await researcher_service.search_researchers(
        session, filters, search_type='ABSTRACT', pagination=filters
    )


@router.get('/researcher/image')
@router.get('/ResearcherData/Image', include_in_schema=False)
async def get_researcher_image(
    session: AsyncSession,
    researcher_id: UUID | None = Query(None),
    name: str | None = Query(None),
    lattes_id: str | None = Query(None),
):
    if not (researcher_id or lattes_id or name):
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST)

    resolved_id = await researcher_service.get_researcher_id_by_params(
        session, lattes_id=lattes_id, name=name, researcher_id=researcher_id
    )

    if not resolved_id:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    path = await researcher_service.get_researcher_image_path(
        session, resolved_id
    )

    if not os.path.exists(path):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    return FileResponse(path)


@router.get('/researcher_filter', response_model=ResearcherFilter)
async def get_researcher_filter(session: AsyncSession):
    return await researcher_service.get_researcher_filter(session)
