from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Integer, and_, case, cast, distinct, func, or_, select

from simcc.core.db.models.graduate_program import GraduateProgram
from simcc.core.db.models.institution import (
    JCR,
    Institution,
    PeriodicalMagazine,
)
from simcc.core.db.models.openalex import OpenAlexArticle, OpenAlexResearcher
from simcc.core.db.models.production import (
    BibliographicProduction,
    BibliographicProductionArticle,
    Brand,
    Foment,
    Guidance,
    ParticipationEvents,
    Patent,
    Publishing,
    ResearchProject,
    ResearchReport,
    Software,
)
from simcc.core.db.models.researcher import Researcher
from simcc.core.db.models.researcher_institution import ResearcherInstitution

RESEARCHERS_TOTAL = 'researchers_total'
TEACHERS_TOTAL = 'teachers_total'
GRADUATE_PROGRAMS_TOTAL = 'graduate_programs_total'
CNPQ_FELLOWS_TOTAL = 'cnpq_fellows_total'
ARTICLES_TOTAL = 'articles_total'
BOOKS_TOTAL = 'books_total'
BOOK_CHAPTERS_TOTAL = 'book_chapters_total'
PATENTS_TOTAL = 'patents_total'
SOFTWARES_TOTAL = 'softwares_total'
BRANDS_TOTAL = 'brands_total'
TECHNICAL_REPORTS_TOTAL = 'technical_reports_total'
GUIDANCE_TOTAL = 'guidance_total'
EVENT_PARTICIPATION_TOTAL = 'event_participation_total'
RESEARCH_PROJECTS_TOTAL = 'research_projects_total'
PUBLISHING_TOTAL = 'publishing_total'
WORKS_IN_EVENTS_TOTAL = 'works_in_events_total'
PERIODICALS_TOTAL = 'periodicals_total'
JCR_RECORDS_TOTAL = 'jcr_records_total'
JCR_ARTICLES_TOTAL = 'jcr_articles_total'
JCR_CITATIONS_TOTAL = 'jcr_citations_total'
JCR_JOURNAL_ARTICLES_TOTAL = 'jcr_journal_articles_total'
OPENALEX_PROFILES_TOTAL = 'openalex_profiles_total'
OPENALEX_WORKS_TOTAL = 'openalex_works_total'
OPENALEX_ARTICLES_TOTAL = 'openalex_articles_total'
OPENALEX_RESEARCHER_CITATIONS_TOTAL = (
    'openalex_researcher_citations_total'
)
OPENALEX_ARTICLE_CITATIONS_TOTAL = 'openalex_article_citations_total'
OPENALEX_I10_TOTAL = 'openalex_i10_total'

GLOBAL = 'GLOBAL'
INSTITUTION = 'INSTITUTION'


@dataclass(frozen=True)
class MetricValue:
    metric_key: str
    scope: str
    value: int
    institution_id: UUID | None = None
    institution_name: str | None = None


async def _global_researcher_count(session, *, teachers: bool) -> int:
    condition = (
        Researcher.docente.is_(True)
        if teachers
        else Researcher.status.is_(True)
    )
    statement = select(func.count(distinct(Researcher.id))).where(condition)
    return int(await session.scalar(statement) or 0)


async def _institutional_researcher_counts(
    session, *, teachers: bool
) -> list[MetricValue]:
    condition = (
        Researcher.docente.is_(True)
        if teachers
        else Researcher.status.is_(True)
    )
    statement = (
        select(
            Institution.id,
            Institution.name,
            func.count(distinct(Researcher.id)),
        )
        .join(
            ResearcherInstitution,
            ResearcherInstitution.institution_id == Institution.id,
        )
        .join(
            Researcher,
            Researcher.id == ResearcherInstitution.researcher_id,
        )
        .where(condition)
        .group_by(Institution.id, Institution.name)
        .order_by(Institution.name)
    )
    rows = (await session.execute(statement)).all()
    metric_key = TEACHERS_TOTAL if teachers else RESEARCHERS_TOTAL
    return [
        MetricValue(
            metric_key=metric_key,
            scope=INSTITUTION,
            institution_id=institution_id,
            institution_name=institution_name,
            value=int(value),
        )
        for institution_id, institution_name, value in rows
    ]


async def get_researchers_metrics(session) -> list[MetricValue]:
    values = [
        MetricValue(
            metric_key=RESEARCHERS_TOTAL,
            scope=GLOBAL,
            value=await _global_researcher_count(session, teachers=False),
        )
    ]
    values.extend(
        await _institutional_researcher_counts(session, teachers=False)
    )
    return values


async def get_teachers_metrics(session) -> list[MetricValue]:
    values = [
        MetricValue(
            metric_key=TEACHERS_TOTAL,
            scope=GLOBAL,
            value=await _global_researcher_count(session, teachers=True),
        )
    ]
    values.extend(
        await _institutional_researcher_counts(session, teachers=True)
    )
    return values


async def _global_count(session, column) -> int:
    statement = select(func.count(column))
    return int(await session.scalar(statement) or 0)


async def get_graduate_programs_metrics(session) -> list[MetricValue]:
    global_value = await _global_count(
        session, GraduateProgram.graduate_program_id
    )
    statement = (
        select(
            Institution.id,
            Institution.name,
            func.count(GraduateProgram.graduate_program_id),
        )
        .join(Institution, Institution.id == GraduateProgram.institution_id)
        .group_by(Institution.id, Institution.name)
        .order_by(Institution.name)
    )
    rows = (await session.execute(statement)).all()
    return [
        MetricValue(
            metric_key=GRADUATE_PROGRAMS_TOTAL,
            scope=GLOBAL,
            value=global_value,
        ),
        *[
            MetricValue(
                metric_key=GRADUATE_PROGRAMS_TOTAL,
                scope=INSTITUTION,
                institution_id=institution_id,
                institution_name=institution_name,
                value=int(value),
            )
            for institution_id, institution_name, value in rows
        ],
    ]


async def _production_metrics(
    session,
    *,
    metric_key: str,
    model,
    conditions=(),
) -> list[MetricValue]:
    global_statement = select(func.count(distinct(model.id))).where(
        *conditions
    )
    global_value = int(await session.scalar(global_statement) or 0)
    institution_statement = (
        select(
            Institution.id,
            Institution.name,
            func.count(distinct(model.id)),
        )
        .join(
            ResearcherInstitution,
            ResearcherInstitution.researcher_id == model.researcher_id,
        )
        .join(
            Institution,
            Institution.id == ResearcherInstitution.institution_id,
        )
        .where(*conditions)
        .group_by(Institution.id, Institution.name)
        .order_by(Institution.name)
    )
    rows = (await session.execute(institution_statement)).all()
    return [
        MetricValue(metric_key=metric_key, scope=GLOBAL, value=global_value),
        *[
            MetricValue(
                metric_key=metric_key,
                scope=INSTITUTION,
                institution_id=institution_id,
                institution_name=institution_name,
                value=int(value),
            )
            for institution_id, institution_name, value in rows
        ],
    ]


async def get_production_metrics(session) -> list[MetricValue]:
    """Return production/listing metrics globally and by institution."""
    specs = (
        (ARTICLES_TOTAL, BibliographicProduction, (
            BibliographicProduction.type == 'ARTICLE',
        )),
        (BOOKS_TOTAL, BibliographicProduction, (
            BibliographicProduction.type == 'BOOK',
        )),
        (BOOK_CHAPTERS_TOTAL, BibliographicProduction, (
            BibliographicProduction.type == 'BOOK_CHAPTER',
        )),
        (WORKS_IN_EVENTS_TOTAL, BibliographicProduction, (
            BibliographicProduction.type == 'WORK_IN_EVENT',
        )),
        (PATENTS_TOTAL, Patent, ()),
        (SOFTWARES_TOTAL, Software, ()),
        (BRANDS_TOTAL, Brand, ()),
        (TECHNICAL_REPORTS_TOTAL, ResearchReport, ()),
        (GUIDANCE_TOTAL, Guidance, ()),
        (EVENT_PARTICIPATION_TOTAL, ParticipationEvents, ()),
        (RESEARCH_PROJECTS_TOTAL, ResearchProject, ()),
        (PUBLISHING_TOTAL, Publishing, ()),
    )
    values: list[MetricValue] = []
    for metric_key, model, conditions in specs:
        values.extend(
            await _production_metrics(
                session,
                metric_key=metric_key,
                model=model,
                conditions=conditions,
            )
        )

    cnpq_condition = and_(
        Foment.scholarship_quantity > 0,
        or_(
            Foment.institute_name.ilike('%cnpq%'),
            Foment.funding_program_name.ilike('%cnpq%'),
        ),
    )
    values.extend(
        await _production_metrics(
            session,
            metric_key=CNPQ_FELLOWS_TOTAL,
            model=Foment,
            conditions=(cnpq_condition,),
        )
    )
    values.append(
        MetricValue(
            metric_key=PERIODICALS_TOTAL,
            scope=GLOBAL,
            value=await _global_count(session, PeriodicalMagazine.id),
        )
    )
    return values


async def _single_global_metric(
    session, metric_key: str, statement
) -> MetricValue:
    return MetricValue(
        metric_key=metric_key,
        scope=GLOBAL,
        value=int(await session.scalar(statement) or 0),
    )


def _numeric_text_sum(column):
    return func.coalesce(
        func.sum(
            case(
                (column.op('~')(r'^[0-9]+$'), cast(column, Integer)),
                else_=0,
            )
        ),
        0,
    )


async def get_jcr_metrics(session) -> list[MetricValue]:
    """Return global JCR volume metrics; JCR has no institution relation."""
    jcr_metrics = [
        await _single_global_metric(
            session,
            JCR_RECORDS_TOTAL,
            select(func.count(JCR.id)),
        ),
        await _single_global_metric(
            session,
            JCR_CITATIONS_TOTAL,
            select(_numeric_text_sum(JCR.totalcites)),
        ),
        await _single_global_metric(
            session,
            JCR_JOURNAL_ARTICLES_TOTAL,
            select(_numeric_text_sum(JCR.totalarticles)),
        ),
    ]
    article_condition = and_(
        BibliographicProductionArticle.jcr.is_not(None),
        BibliographicProductionArticle.jcr.notin_(['', 'N/A']),
    )
    jcr_article_statement = (
        select(func.count(distinct(BibliographicProduction.id)))
        .join(
            BibliographicProductionArticle,
            BibliographicProductionArticle.bibliographic_production_id
            == BibliographicProduction.id,
        )
        .where(
            BibliographicProduction.type == 'ARTICLE',
            article_condition,
        )
    )
    jcr_metrics.append(
        await _single_global_metric(
            session, JCR_ARTICLES_TOTAL, jcr_article_statement
        )
    )
    return jcr_metrics


async def _openalex_researcher_metrics(
    session,
    *,
    metric_key: str,
    column,
) -> list[MetricValue]:
    aggregate = (
        func.count(distinct(column))
        if metric_key == OPENALEX_PROFILES_TOTAL
        else func.coalesce(func.sum(column), 0)
    )
    global_statement = select(aggregate)
    institution_aggregate = (
        func.count(distinct(column))
        if metric_key == OPENALEX_PROFILES_TOTAL
        else func.coalesce(func.sum(column), 0)
    )
    global_value = int(await session.scalar(global_statement) or 0)
    institution_statement = (
        select(
            Institution.id,
            Institution.name,
            institution_aggregate,
        )
        .join(
            ResearcherInstitution,
            ResearcherInstitution.researcher_id
            == OpenAlexResearcher.researcher_id,
        )
        .join(
            Institution,
            Institution.id == ResearcherInstitution.institution_id,
        )
        .group_by(Institution.id, Institution.name)
        .order_by(Institution.name)
    )
    rows = (await session.execute(institution_statement)).all()
    return [
        MetricValue(metric_key=metric_key, scope=GLOBAL, value=global_value),
        *[
            MetricValue(
                metric_key=metric_key,
                scope=INSTITUTION,
                institution_id=institution_id,
                institution_name=institution_name,
                value=int(value),
            )
            for institution_id, institution_name, value in rows
        ],
    ]


async def _openalex_article_metrics(
    session,
    *,
    metric_key: str,
    column,
) -> list[MetricValue]:
    is_count = metric_key == OPENALEX_ARTICLES_TOTAL
    global_aggregate = (
        func.count(distinct(OpenAlexArticle.id))
        if is_count
        else func.coalesce(func.sum(column), 0)
    )
    institution_aggregate = (
        func.count(distinct(OpenAlexArticle.id))
        if is_count
        else func.coalesce(func.sum(column), 0)
    )
    global_statement = select(global_aggregate)
    global_value = int(await session.scalar(global_statement) or 0)
    institution_statement = (
        select(
            Institution.id,
            Institution.name,
            institution_aggregate,
        )
        .join(
            BibliographicProduction,
            BibliographicProduction.id == OpenAlexArticle.article_id,
        )
        .join(
            ResearcherInstitution,
            ResearcherInstitution.researcher_id
            == BibliographicProduction.researcher_id,
        )
        .join(
            Institution,
            Institution.id == ResearcherInstitution.institution_id,
        )
        .group_by(Institution.id, Institution.name)
        .order_by(Institution.name)
    )
    rows = (await session.execute(institution_statement)).all()
    return [
        MetricValue(metric_key=metric_key, scope=GLOBAL, value=global_value),
        *[
            MetricValue(
                metric_key=metric_key,
                scope=INSTITUTION,
                institution_id=institution_id,
                institution_name=institution_name,
                value=int(value),
            )
            for institution_id, institution_name, value in rows
        ],
    ]


async def get_openalex_metrics(session) -> list[MetricValue]:
    """Return OpenAlex totals globally and by researcher institution."""
    values: list[MetricValue] = []
    researcher_specs = (
        (OPENALEX_PROFILES_TOTAL, OpenAlexResearcher.researcher_id),
        (OPENALEX_WORKS_TOTAL, OpenAlexResearcher.works_count),
        (
            OPENALEX_RESEARCHER_CITATIONS_TOTAL,
            OpenAlexResearcher.cited_by_count,
        ),
        (OPENALEX_I10_TOTAL, OpenAlexResearcher.i10_index),
    )
    for metric_key, column in researcher_specs:
        values.extend(
            await _openalex_researcher_metrics(
                session, metric_key=metric_key, column=column
            )
        )
    values.extend(
        await _openalex_article_metrics(
            session,
            metric_key=OPENALEX_ARTICLES_TOTAL,
            column=func.count(OpenAlexArticle.id),
        )
    )
    values.extend(
        await _openalex_article_metrics(
            session,
            metric_key=OPENALEX_ARTICLE_CITATIONS_TOTAL,
            column=OpenAlexArticle.citations_count,
        )
    )
    return values


async def get_initial_metrics(session) -> list[MetricValue]:
    """Return every metric in the consistency catalog."""
    values: list[MetricValue] = []
    values.extend(await get_teachers_metrics(session))
    values.extend(await get_researchers_metrics(session))
    values.extend(await get_graduate_programs_metrics(session))
    values.extend(await get_production_metrics(session))
    values.extend(await get_jcr_metrics(session))
    values.extend(await get_openalex_metrics(session))
    return values
