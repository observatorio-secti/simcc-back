from fastapi import APIRouter, Query

from simcc.core.dependencies import AsyncSession, Filters
from simcc.schemas.research_group import ResearchGroupAreaCount
from simcc.schemas.researcher import (
    AcademicDegree,
    ArticleMetric,
    EducationMetric,
    GreatArea,
    GuidanceMetric,
    LattesUpdateMetric,
    PatentMetric,
    ResearcherCountMetric,
    ResearchProjectMetric,
    ScholarshipMetric,
    SpeakerMetric,
    YearlyMetric,
)
from simcc.services import research_group_service, researcher_service

router = APIRouter(tags=['Metrics'])


@router.get(
    '/metrics/academic-degree/chart', response_model=list[AcademicDegree]
)
@router.get('/academic_degree', include_in_schema=False)
async def get_academic_degree(
    session: AsyncSession,
    filters: Filters,
):
    return await researcher_service.get_metrics_academic_degree(
        session, filters
    )


@router.get('/metrics/great-area/chart', response_model=list[GreatArea])
@router.get('/great_area', include_in_schema=False)
async def get_great_area(
    session: AsyncSession,
    filters: Filters,
):
    return await researcher_service.get_metrics_great_area(session, filters)


@router.get('/metrics/magazine/chart')
@router.get('/magazine_metrics', include_in_schema=False)
async def get_magazine_metrics(
    session: AsyncSession,
    issn: str | None = Query(None),
    initials: str | None = Query(None),
):
    return await researcher_service.get_metrics_magazine(
        session, issn=issn, initials=initials
    )


@router.get(
    '/metrics/researcher/chart', response_model=list[ResearcherCountMetric]
)
@router.get('/researcher_metrics', include_in_schema=False)
async def get_researcher_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_researcher(session, filters)


@router.get('/metrics/brand/chart', response_model=list[YearlyMetric])
@router.get('/brand_metrics', include_in_schema=False)
async def get_brand_metrics(
    session: AsyncSession, filters: Filters, nature: str | None = Query(None)
):
    return await researcher_service.get_metrics_brand(
        session, filters, nature=nature
    )


@router.get('/metrics/speaker/chart', response_model=list[SpeakerMetric])
@router.get('/speaker_metrics', include_in_schema=False)
async def get_speaker_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_speaker(session, filters)


@router.get(
    '/metrics/research-report/chart', response_model=list[YearlyMetric]
)
@router.get('/research_report_metrics', include_in_schema=False)
async def get_research_report_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_research_report(
        session, filters
    )


@router.get('/metrics/events/chart', response_model=list[YearlyMetric])
@router.get('/events_metrics', include_in_schema=False)
async def get_events_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_yearly_production(
        session, filters, 'WORK_IN_EVENT'
    )


@router.get(
    '/metrics/papers-magazine/chart', response_model=list[YearlyMetric]
)
@router.get('/papers_magazine_metrics', include_in_schema=False)
async def get_papers_magazine_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_yearly_production(
        session, filters, 'TEXT_IN_NEWSPAPER_MAGAZINE'
    )


@router.get('/metrics/book/chart', response_model=list[YearlyMetric])
@router.get('/book_metrics', include_in_schema=False)
async def get_book_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_yearly_production(
        session, filters, 'BOOK'
    )


@router.get('/metrics/book-chapter/chart', response_model=list[YearlyMetric])
@router.get('/book_chapter_metrics', include_in_schema=False)
async def get_book_chapter_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_yearly_production(
        session, filters, 'BOOK_CHAPTER'
    )


@router.get('/metrics/article/chart', response_model=list[ArticleMetric])
@router.get('/article_metrics', include_in_schema=False)
async def get_article_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_yearly_production(
        session, filters, 'ARTICLE'
    )


@router.get('/metrics/patent/chart', response_model=list[PatentMetric])
@router.get('/patent_metrics', include_in_schema=False)
async def get_patent_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_patents(session, filters)


@router.get('/metrics/guidance/chart', response_model=list[GuidanceMetric])
@router.get('/guidance_metrics', include_in_schema=False)
async def get_guidance_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_guidance(session, filters)


@router.get('/metrics/education/chart', response_model=list[EducationMetric])
@router.get('/academic_degree_metrics', include_in_schema=False)
async def get_academic_degree_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_education(session, filters)


@router.get('/metrics/software/chart', response_model=list[YearlyMetric])
@router.get('/software_metrics', include_in_schema=False)
async def get_software_metrics(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_software(session, filters)


@router.get(
    '/metrics/research-project/chart',
    response_model=list[ResearchProjectMetric],
)
@router.get('/research_project_metrics', include_in_schema=False)
async def get_research_project_metrics(
    session: AsyncSession, filters: Filters
):
    return await researcher_service.get_metrics_research_project(
        session, filters
    )


@router.get(
    '/metrics/lattes-update/chart',
    response_model=list[LattesUpdateMetric],
)
@router.get('/lattes_update', include_in_schema=False)
async def get_lattes_update(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_lattes_update(session, filters)


@router.get(
    '/metrics/researcher/scholarship', response_model=list[ScholarshipMetric]
)
async def get_metrics_scholarship(session: AsyncSession, filters: Filters):
    return await researcher_service.get_metrics_scholarship(session, filters)


@router.get(
    '/metrics/research-group/chart',
    response_model=list[ResearchGroupAreaCount],
)
@router.get('/metrics/research_group/chart', include_in_schema=False)
async def get_research_group_chart(session: AsyncSession, filters: Filters):
    return await research_group_service.count_research_groups_by_area(
        session, filters
    )
