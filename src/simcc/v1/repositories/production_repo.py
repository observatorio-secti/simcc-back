from sqlalchemy import text

from simcc.v1.queries import production_query
from simcc.v1.queries.metrics_query import (
    GeneralProductionMetricsQuery,
    GraduateProgramProductionQuery,
)
from simcc.v1.repositories.common import build_common_filters


async def list_professional_experience(session, filters):
    query = production_query.ProfessionalExperienceQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_patent(session, filters):
    query = production_query.PatentQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_participation_event(session, filters):
    query = production_query.ParticipationEventQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_brand(session, filters):
    query = production_query.BrandQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_researcher_report(session, filters):
    query = production_query.ReportQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_software(session, filters):
    query = production_query.SoftwareQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_guidance_production(session, filters):
    query = production_query.GuidanceQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_research_projects(session, filters):
    query = production_query.ResearchProjectQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_researcher_production_events(session, filters):
    query = production_query.EventArticleQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_researcher_scholarships(session, filters):
    query = production_query.ScholarshipQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def get_graduate_program_production(session, filters):
    query = GraduateProgramProductionQuery(session)
    query.apply_filters(filters)
    return await query.execute()


async def list_general_production_metrics(session, filters):
    query = GeneralProductionMetricsQuery(session)
    query.apply_filters(filters)
    return await query.execute()


async def list_papers_magazine(session, filters):
    cf = build_common_filters(filters, table_alias='bp', year_col='year_')

    FILTERS_SQL = (
        "AND bp.type = 'TEXT_IN_NEWSPAPER_MAGAZINE'" + cf['filters_sql']
    )

    SCRIPT_SQL = f"""
        SELECT {cf['distinct_sql']}
            title, title_en, nature, language, means_divulgation, homepage,
            relevance, scientific_divulgation, authors, year_, r.name,
            bp.id, bp.researcher_id, r.lattes_id
        FROM public.bibliographic_production bp
            INNER JOIN researcher r ON bp.researcher_id = r.id
            {cf['joins']['researcher_production']}
            {cf['joins']['foment']}
            {cf['joins']['program']}
            {cf['joins']['departament']}
            {cf['joins']['institution']}
            {cf['joins']['group']}
        WHERE 1 = 1
            {FILTERS_SQL}
        ORDER BY {'bp.title, bp.year_ DESC' if cf['distinct_sql'] else 'bp.year_ DESC'}
        {cf['filter_pagination']};
    """
    result = await session.execute(text(SCRIPT_SQL), cf['params'])
    return result.mappings().all()


async def list_magazine(session, filters):
    query = production_query.MagazineSearchQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_recently_updated(session, filters):
    query = production_query.RecentlyUpdatedQuery(session)
    query.apply_filters(filters)
    return await query.execute()


async def list_bibliographic_production(session, filters, qualis: str | None):
    cf = build_common_filters(filters, table_alias='b', year_col='year')

    params = cf['params']
    FILTERS_SQL = cf['filters_sql']

    if qualis:
        params['qualis'] = qualis.split(';')
        FILTERS_SQL += ' AND bpa.qualis = ANY(:qualis)'

    SCRIPT_SQL = f"""
        SELECT {cf['distinct_sql']}
            b.id AS id, title, b.year, b.type, doi, bpa.qualis,
            periodical_magazine_name AS magazine, r.name AS researcher,
            r.lattes_10_id, r.lattes_id, jcr AS jif,
            jcr_link, r.id AS researcher_id, opa.abstract,
            opa.article_institution, opa.authors, opa.authors_institution,
            COALESCE (opa.citations_count, 0) AS citations_count, bpa.issn,
            opa.keywords, opa.landing_page_url, opa.language, opa.pdf,
            b.has_image, b.relevance, bpa.stars, bpa.quadrennial
        FROM bibliographic_production b
            LEFT JOIN bibliographic_production_article bpa ON b.id = bpa.bibliographic_production_id
            LEFT JOIN researcher r ON r.id = b.researcher_id
            LEFT JOIN openalex_article opa ON opa.article_id = b.id
            {cf['joins']['institution']}
            {cf['joins']['researcher_production']}
            {cf['joins']['foment']}
            {cf['joins']['program']}
            {cf['joins']['departament']}
            {cf['joins']['group']}
        WHERE 1 = 1
            {FILTERS_SQL}
        ORDER BY {'b.title, b.year DESC' if cf['distinct_sql'] else 'b.year DESC'}
        {cf['filter_pagination']};
    """
    result = await session.execute(text(SCRIPT_SQL), params)
    return result.mappings().all()


async def list_book_chapter(session, filters):
    cf = build_common_filters(filters, table_alias='bp', year_col='year')

    SCRIPT_SQL = f"""
        SELECT {cf['distinct_sql']}
            bp.title, bp.year, bpc.isbn, bpc.publishing_company,
            bp.researcher_id AS researcher, bp.id, r.lattes_id, bp.relevance,
            bp.has_image, r.name
        FROM bibliographic_production bp
            INNER JOIN bibliographic_production_book_chapter bpc ON bpc.bibliographic_production_id = bp.id
            LEFT JOIN researcher r ON r.id = bp.researcher_id
            {cf['joins']['researcher_production']}
            {cf['joins']['foment']}
            {cf['joins']['program']}
            {cf['joins']['departament']}
            {cf['joins']['institution']}
            {cf['joins']['group']}
        WHERE 1 = 1
            {cf['filters_sql']}
        ORDER BY {'bp.title, bp.year DESC' if cf['distinct_sql'] else 'bp.year DESC'}
        {cf['filter_pagination']};
    """
    result = await session.execute(text(SCRIPT_SQL), cf['params'])
    return result.mappings().all()


async def list_book(session, filters):
    cf = build_common_filters(filters, table_alias='bp', year_col='year')

    SCRIPT_SQL = f"""
        SELECT {cf['distinct_sql']}
            bp.title, bp.year, bpb.isbn AS isbn,
            bpb.publishing_company AS publishing_company,
            bp.researcher_id AS researcher,
            r.lattes_id AS lattes_id, bp.relevance,
            bp.has_image, bp.id, r.name, bpb.stars
        FROM public.bibliographic_production bp
            INNER JOIN public.bibliographic_production_book bpb ON bp.id = bpb.bibliographic_production_id
            INNER JOIN public.researcher r ON r.id = bp.researcher_id
            {cf['joins']['researcher_production']}
            {cf['joins']['foment']}
            {cf['joins']['program']}
            {cf['joins']['departament']}
            {cf['joins']['institution']}
            {cf['joins']['group']}
        WHERE 1 = 1
            {cf['filters_sql']}
        ORDER BY {'bp.title, bp.year DESC' if cf['distinct_sql'] else 'bp.year DESC, bp.title ASC'}
        {cf['filter_pagination']};
    """
    result = await session.execute(text(SCRIPT_SQL), cf['params'])
    return result.mappings().all()
