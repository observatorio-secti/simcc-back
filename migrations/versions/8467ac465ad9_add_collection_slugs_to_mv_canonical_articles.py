# ruff: noqa: E501
"""add_collection_slugs_to_mv_canonical_articles_and_productions

Revision ID: 8467ac465ad9
Revises: bfc27c732497
Create Date: 2026-11-06 06:42:06.181127

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8467ac465ad9'
down_revision: Union[str, Sequence[str], None] = 'bfc27c732497'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CANONICAL_VIEWS = [
    'mv_canonical_articles',
    'mv_canonical_books',
    'mv_canonical_book_chapters',
    'mv_canonical_software',
    'mv_canonical_patents',
    'mv_canonical_events',
    'mv_canonical_research_projects',
]

COMMON_INDEXES = [
    # 1. Artigos
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_articles_pk ON mv_canonical_articles (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_doi ON mv_canonical_articles (doi);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_year ON mv_canonical_articles (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_citations ON mv_canonical_articles (citations_count DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_qualis ON mv_canonical_articles (qualis);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_researchers ON mv_canonical_articles USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_institutions ON mv_canonical_articles USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_programs ON mv_canonical_articles USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_prods ON mv_canonical_articles USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_vector ON mv_canonical_articles USING GIN (search_vector);',
    # 2. Livros
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_books_pk ON mv_canonical_books (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_isbn ON mv_canonical_books (isbn);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_year ON mv_canonical_books (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_researchers ON mv_canonical_books USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_institutions ON mv_canonical_books USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_programs ON mv_canonical_books USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_prods ON mv_canonical_books USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_vector ON mv_canonical_books USING GIN (search_vector);',
    # 3. Capítulos de Livros
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_chapters_pk ON mv_canonical_book_chapters (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_isbn ON mv_canonical_book_chapters (isbn);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_year ON mv_canonical_book_chapters (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_researchers ON mv_canonical_book_chapters USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_institutions ON mv_canonical_book_chapters USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_programs ON mv_canonical_book_chapters USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_prods ON mv_canonical_book_chapters USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_vector ON mv_canonical_book_chapters USING GIN (search_vector);',
    # 4. Softwares
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_software_pk ON mv_canonical_software (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_code ON mv_canonical_software (code);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_year ON mv_canonical_software (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_researchers ON mv_canonical_software USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_institutions ON mv_canonical_software USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_programs ON mv_canonical_software USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_prods ON mv_canonical_software USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_vector ON mv_canonical_software USING GIN (search_vector);',
    # 5. Patentes
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_patents_pk ON mv_canonical_patents (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_code ON mv_canonical_patents (code);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_year ON mv_canonical_patents (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_researchers ON mv_canonical_patents USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_institutions ON mv_canonical_patents USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_programs ON mv_canonical_patents USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_prods ON mv_canonical_patents USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_vector ON mv_canonical_patents USING GIN (search_vector);',
    # 6. Eventos
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_events_pk ON mv_canonical_events (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_year ON mv_canonical_events (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_researchers ON mv_canonical_events USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_institutions ON mv_canonical_events USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_programs ON mv_canonical_events USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_prods ON mv_canonical_events USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_vector ON mv_canonical_events USING GIN (search_vector);',
    # 7. Projetos de Pesquisa
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_projects_pk ON mv_canonical_research_projects (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_year ON mv_canonical_research_projects (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_researchers ON mv_canonical_research_projects USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_institutions ON mv_canonical_research_projects USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_programs ON mv_canonical_research_projects USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_prods ON mv_canonical_research_projects USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_vector ON mv_canonical_research_projects USING GIN (search_vector);',
]

COLLECTION_SLUG_INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_collection_slugs ON mv_canonical_articles USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_collection_slugs ON mv_canonical_books USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_collection_slugs ON mv_canonical_book_chapters USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_collection_slugs ON mv_canonical_software USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_collection_slugs ON mv_canonical_patents USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_collection_slugs ON mv_canonical_events USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_collection_slugs ON mv_canonical_research_projects USING GIN (collection_slugs);',
]


def upgrade() -> None:
    for view in reversed(CANONICAL_VIEWS):
        op.execute(f'DROP MATERIALIZED VIEW IF EXISTS {view} CASCADE;')

    # 1. ARTIGOS
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_articles AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(bp.id))[1] AS canonical_id,
            ARRAY_AGG(bp.id) AS production_ids,
            ARRAY_AGG(DISTINCT bp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            bp.title,
            bp.year_,
            bp.doi,
            MAX(bpa.qualis) AS qualis,
            MAX(bpa.jcr) AS jcr,
            MAX(bpa.periodical_magazine_name) AS magazine_name,
            MAX(bpa.issn) AS issn,
            MAX(oa.abstract) AS abstract,
            COALESCE(MAX(oa.citations_count), 0) AS citations_count,
            MAX(oa.landing_page_url) AS landing_page_url,
            MAX(oa.pdf) AS pdf_url,
            MAX(oa.keywords) AS keywords,
            MAX(bp.authors) AS all_authors_raw,
            MAX(oa.language) AS language
        FROM bibliographic_production bp
        JOIN bibliographic_production_article bpa ON bpa.bibliographic_production_id = bp.id
        LEFT JOIN researcher r ON r.id = bp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = bp.researcher_id
        LEFT JOIN openalex_article oa ON oa.article_id = bp.id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = bp.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        WHERE bp.type = 'ARTICLE'
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(bp.doi)), ''), LOWER(UNACCENT(TRIM(bp.title)))),
            bp.title,
            bp.year_,
            bp.doi
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        COALESCE(collection_slugs, '{}') AS collection_slugs,
        platform_authors,
        title,
        year_ AS year,
        doi,
        qualis,
        jcr,
        magazine_name,
        issn,
        abstract,
        citations_count,
        landing_page_url,
        pdf_url,
        keywords,
        all_authors_raw,
        language,
        (abstract IS NOT NULL AND length(abstract) > 0) AS has_abstract,
        (pdf_url IS NOT NULL AND length(pdf_url) > 0) AS has_open_access_pdf,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(keywords, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(abstract, '')), 'C')
            || setweight(to_tsvector('pt_unaccent', coalesce(magazine_name, '') || ' ' || coalesce(issn, '')), 'D')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 2. LIVROS
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_books AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(bp.id))[1] AS canonical_id,
            ARRAY_AGG(bp.id) AS production_ids,
            ARRAY_AGG(DISTINCT bp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            bp.title,
            bp.year_,
            bp.doi,
            MAX(bpb.isbn) AS isbn,
            MAX(bpb.publishing_company) AS publishing_company,
            MAX(bpb.publishing_company_city) AS publishing_company_city,
            MAX(bp.authors) AS all_authors_raw
        FROM bibliographic_production bp
        JOIN bibliographic_production_book bpb ON bpb.bibliographic_production_id = bp.id
        LEFT JOIN researcher r ON r.id = bp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = bp.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = bp.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        WHERE bp.type = 'BOOK'
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(bpb.isbn)), ''), LOWER(UNACCENT(TRIM(bp.title)))),
            bp.title,
            bp.year_,
            bp.doi
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        COALESCE(collection_slugs, '{}') AS collection_slugs,
        platform_authors,
        title,
        year_ AS year,
        doi,
        isbn,
        publishing_company,
        publishing_company_city,
        all_authors_raw,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(publishing_company, '') || ' ' || coalesce(publishing_company_city, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(isbn, '')), 'C')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 3. CAPÍTULOS DE LIVROS
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_book_chapters AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(bp.id))[1] AS canonical_id,
            ARRAY_AGG(bp.id) AS production_ids,
            ARRAY_AGG(DISTINCT bp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            bp.title,
            bp.year_,
            bp.doi,
            MAX(bpc.isbn) AS isbn,
            MAX(bpc.book_title) AS book_title,
            MAX(bpc.publishing_company) AS publishing_company,
            MAX(bpc.organizers) AS organizers,
            MAX(bpc.start_page) AS start_page,
            MAX(bpc.end_page) AS end_page,
            MAX(bp.authors) AS all_authors_raw
        FROM bibliographic_production bp
        JOIN bibliographic_production_book_chapter bpc ON bpc.bibliographic_production_id = bp.id
        LEFT JOIN researcher r ON r.id = bp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = bp.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = bp.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        WHERE bp.type = 'BOOK_CHAPTER'
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(bpc.isbn)), ''), LOWER(UNACCENT(TRIM(bp.title))) || '_' || LOWER(UNACCENT(TRIM(COALESCE(bpc.book_title, ''))))),
            bp.title,
            bp.year_,
            bp.doi
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        COALESCE(collection_slugs, '{}') AS collection_slugs,
        platform_authors,
        title,
        year_ AS year,
        doi,
        isbn,
        book_title,
        publishing_company,
        organizers,
        start_page,
        end_page,
        all_authors_raw,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(book_title, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(publishing_company, '') || ' ' || coalesce(organizers, '')), 'C')
            || setweight(to_tsvector('pt_unaccent', coalesce(isbn, '')), 'D')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 4. SOFTWARES
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_software AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(sw.id))[1] AS canonical_id,
            ARRAY_AGG(sw.id) AS production_ids,
            ARRAY_AGG(DISTINCT sw.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            sw.title,
            sw.year,
            MAX(sw.platform) AS platform,
            MAX(sw.environment) AS environment,
            MAX(sw.code) AS code,
            MAX(sw.availability) AS availability,
            MAX(sw.financing_institutionc) AS financing
        FROM software sw
        LEFT JOIN researcher r ON r.id = sw.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = sw.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = sw.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(sw.code)), ''), LOWER(UNACCENT(TRIM(sw.title))) || '_' || COALESCE(sw.year::text, '')),
            sw.title,
            sw.year
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        COALESCE(collection_slugs, '{}') AS collection_slugs,
        platform_authors,
        title,
        year,
        platform,
        environment,
        code,
        availability,
        financing,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(platform, '') || ' ' || coalesce(environment, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(code, '')), 'C')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 5. PATENTES
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_patents AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(p.id))[1] AS canonical_id,
            ARRAY_AGG(p.id) AS production_ids,
            ARRAY_AGG(DISTINCT p.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            p.title,
            COALESCE(MAX(NULLIF(p.development_year, '')::int), EXTRACT(YEAR FROM MAX(p.grant_date))::int) AS year,
            MAX(p.grant_date) AS grant_date,
            MAX(p.deposit_date) AS deposit_date,
            MAX(p.category) AS category,
            MAX(p.code) AS code,
            MAX(p.details) AS details
        FROM patent p
        LEFT JOIN researcher r ON r.id = p.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = p.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = p.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(p.code)), ''), LOWER(UNACCENT(TRIM(p.title)))),
            p.title
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        COALESCE(collection_slugs, '{}') AS collection_slugs,
        platform_authors,
        title,
        year,
        grant_date,
        deposit_date,
        category,
        code,
        details,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(category, '') || ' ' || coalesce(details, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(code, '')), 'C')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 6. PARTICIPAÇÃO EM EVENTOS
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_events AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(pe.id))[1] AS canonical_id,
            ARRAY_AGG(pe.id) AS production_ids,
            ARRAY_AGG(DISTINCT pe.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            pe.title,
            pe.event_name,
            pe.year,
            MAX(pe.nature) AS nature,
            MAX(pe.type_participation) AS type_participation,
            MAX(pe.form_participation) AS form_participation
        FROM participation_events pe
        LEFT JOIN researcher r ON r.id = pe.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = pe.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = pe.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(pe.title)), ''), LOWER(UNACCENT(TRIM(pe.event_name)))) || '_' || COALESCE(pe.year::text, ''),
            pe.title,
            pe.event_name,
            pe.year
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        COALESCE(collection_slugs, '{}') AS collection_slugs,
        platform_authors,
        title,
        event_name,
        year,
        nature,
        type_participation,
        form_participation,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(event_name, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(nature, '') || ' ' || coalesce(type_participation, '')), 'C')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 7. PROJETOS DE PESQUISA
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_research_projects AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(rp.id ORDER BY rp.id))[1] AS canonical_id,
            ARRAY_AGG(DISTINCT rp.id) AS production_ids,
            ARRAY_AGG(DISTINCT rp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            MAX(rp.project_name) AS title,
            rp.start_year,
            MAX(rp.end_year) AS end_year,
            MAX(rp.status) AS status,
            MAX(rp.nature) AS nature,
            MAX(rp.agency_name) AS agency_name,
            MAX(rp.agency_code) AS agency_code,
            MAX(rp.description) AS description,
            MAX(rp.number_undergraduates) AS number_undergraduates,
            MAX(rp.number_specialists) AS number_specialists,
            MAX(rp.number_academic_masters) AS number_academic_masters,
            MAX(rp.number_phd) AS number_phd
        FROM research_project rp
        LEFT JOIN researcher r ON r.id = rp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = rp.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = rp.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        WHERE NULLIF(TRIM(rp.project_name), '') IS NOT NULL
        GROUP BY
            LOWER(UNACCENT(TRIM(rp.project_name))),
            rp.start_year
    )
    SELECT
        d.canonical_id,
        d.production_ids,
        d.researcher_ids,
        d.institution_ids,
        d.graduate_program_ids,
        COALESCE(d.collection_slugs, '{}') AS collection_slugs,
        d.platform_authors,
        d.title,
        d.start_year AS year,
        d.start_year,
        d.end_year,
        d.status,
        d.nature,
        d.agency_name,
        d.agency_code,
        d.description,
        d.number_undergraduates,
        d.number_specialists,
        d.number_academic_masters,
        d.number_phd,
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'agency_name', f.agency_name,
                'agency_code', f.agency_code,
                'nature', f.nature
            ))
            FROM research_project_foment f
            WHERE f.project_id = ANY(d.production_ids)
        ) AS foment,
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'name', c.name,
                'lattes_id', c.lattes_id,
                'citations', c.citations,
                'coordinator', c.coordinator
            ))
            FROM research_project_components c
            WHERE c.project_id = ANY(d.production_ids)
        ) AS components,
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'title', p.title,
                'type', p.type
            ))
            FROM research_project_production p
            WHERE p.project_id = ANY(d.production_ids)
        ) AS productions,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(d.title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(d.description, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(d.agency_name, '') || ' ' || coalesce(d.nature, '')), 'C')
        ) AS search_vector
    FROM deduplicated d;
    """)

    for idx in COMMON_INDEXES + COLLECTION_SLUG_INDEXES:
        op.execute(idx)


def downgrade() -> None:
    for view in reversed(CANONICAL_VIEWS):
        op.execute(f'DROP MATERIALIZED VIEW IF EXISTS {view} CASCADE;')

    # 1. ARTIGOS
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_articles AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(bp.id))[1] AS canonical_id,
            ARRAY_AGG(bp.id) AS production_ids,
            ARRAY_AGG(DISTINCT bp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            bp.title,
            bp.year_,
            bp.doi,
            MAX(bpa.qualis) AS qualis,
            MAX(bpa.jcr) AS jcr,
            MAX(bpa.periodical_magazine_name) AS magazine_name,
            MAX(bpa.issn) AS issn,
            MAX(oa.abstract) AS abstract,
            COALESCE(MAX(oa.citations_count), 0) AS citations_count,
            MAX(oa.landing_page_url) AS landing_page_url,
            MAX(oa.pdf) AS pdf_url,
            MAX(oa.keywords) AS keywords,
            MAX(bp.authors) AS all_authors_raw,
            MAX(oa.language) AS language
        FROM bibliographic_production bp
        JOIN bibliographic_production_article bpa ON bpa.bibliographic_production_id = bp.id
        LEFT JOIN researcher r ON r.id = bp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = bp.researcher_id
        LEFT JOIN openalex_article oa ON oa.article_id = bp.id
        WHERE bp.type = 'ARTICLE'
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(bp.doi)), ''), LOWER(UNACCENT(TRIM(bp.title)))),
            bp.title,
            bp.year_,
            bp.doi
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        platform_authors,
        title,
        year_ AS year,
        doi,
        qualis,
        jcr,
        magazine_name,
        issn,
        abstract,
        citations_count,
        landing_page_url,
        pdf_url,
        keywords,
        all_authors_raw,
        language,
        (abstract IS NOT NULL AND length(abstract) > 0) AS has_abstract,
        (pdf_url IS NOT NULL AND length(pdf_url) > 0) AS has_open_access_pdf,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(keywords, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(abstract, '')), 'C')
            || setweight(to_tsvector('pt_unaccent', coalesce(magazine_name, '') || ' ' || coalesce(issn, '')), 'D')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 2. LIVROS
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_books AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(bp.id))[1] AS canonical_id,
            ARRAY_AGG(bp.id) AS production_ids,
            ARRAY_AGG(DISTINCT bp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            bp.title,
            bp.year_,
            bp.doi,
            MAX(bpb.isbn) AS isbn,
            MAX(bpb.publishing_company) AS publishing_company,
            MAX(bpb.publishing_company_city) AS publishing_company_city,
            MAX(bp.authors) AS all_authors_raw
        FROM bibliographic_production bp
        JOIN bibliographic_production_book bpb ON bpb.bibliographic_production_id = bp.id
        LEFT JOIN researcher r ON r.id = bp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = bp.researcher_id
        WHERE bp.type = 'BOOK'
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(bpb.isbn)), ''), LOWER(UNACCENT(TRIM(bp.title)))),
            bp.title,
            bp.year_,
            bp.doi
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        platform_authors,
        title,
        year_ AS year,
        doi,
        isbn,
        publishing_company,
        publishing_company_city,
        all_authors_raw,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(publishing_company, '') || ' ' || coalesce(publishing_company_city, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(isbn, '')), 'C')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 3. CAPÍTULOS DE LIVROS
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_book_chapters AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(bp.id))[1] AS canonical_id,
            ARRAY_AGG(bp.id) AS production_ids,
            ARRAY_AGG(DISTINCT bp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            bp.title,
            bp.year_,
            bp.doi,
            MAX(bpc.isbn) AS isbn,
            MAX(bpc.book_title) AS book_title,
            MAX(bpc.publishing_company) AS publishing_company,
            MAX(bpc.organizers) AS organizers,
            MAX(bpc.start_page) AS start_page,
            MAX(bpc.end_page) AS end_page,
            MAX(bp.authors) AS all_authors_raw
        FROM bibliographic_production bp
        JOIN bibliographic_production_book_chapter bpc ON bpc.bibliographic_production_id = bp.id
        LEFT JOIN researcher r ON r.id = bp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = bp.researcher_id
        WHERE bp.type = 'BOOK_CHAPTER'
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(bpc.isbn)), ''), LOWER(UNACCENT(TRIM(bp.title))) || '_' || LOWER(UNACCENT(TRIM(COALESCE(bpc.book_title, ''))))),
            bp.title,
            bp.year_,
            bp.doi
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        platform_authors,
        title,
        year_ AS year,
        doi,
        isbn,
        book_title,
        publishing_company,
        organizers,
        start_page,
        end_page,
        all_authors_raw,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(book_title, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(publishing_company, '') || ' ' || coalesce(organizers, '')), 'C')
            || setweight(to_tsvector('pt_unaccent', coalesce(isbn, '')), 'D')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 4. SOFTWARES
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_software AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(sw.id))[1] AS canonical_id,
            ARRAY_AGG(sw.id) AS production_ids,
            ARRAY_AGG(DISTINCT sw.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            sw.title,
            sw.year,
            MAX(sw.platform) AS platform,
            MAX(sw.environment) AS environment,
            MAX(sw.code) AS code,
            MAX(sw.availability) AS availability,
            MAX(sw.financing_institutionc) AS financing
        FROM software sw
        LEFT JOIN researcher r ON r.id = sw.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = sw.researcher_id
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(sw.code)), ''), LOWER(UNACCENT(TRIM(sw.title))) || '_' || COALESCE(sw.year::text, '')),
            sw.title,
            sw.year
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        platform_authors,
        title,
        year,
        platform,
        environment,
        code,
        availability,
        financing,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(platform, '') || ' ' || coalesce(environment, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(code, '')), 'C')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 5. PATENTES
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_patents AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(p.id))[1] AS canonical_id,
            ARRAY_AGG(p.id) AS production_ids,
            ARRAY_AGG(DISTINCT p.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            p.title,
            COALESCE(MAX(NULLIF(p.development_year, '')::int), EXTRACT(YEAR FROM MAX(p.grant_date))::int) AS year,
            MAX(p.grant_date) AS grant_date,
            MAX(p.deposit_date) AS deposit_date,
            MAX(p.category) AS category,
            MAX(p.code) AS code,
            MAX(p.details) AS details
        FROM patent p
        LEFT JOIN researcher r ON r.id = p.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = p.researcher_id
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(p.code)), ''), LOWER(UNACCENT(TRIM(p.title)))),
            p.title
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        platform_authors,
        title,
        year,
        grant_date,
        deposit_date,
        category,
        code,
        details,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(category, '') || ' ' || coalesce(details, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(code, '')), 'C')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 6. PARTICIPAÇÃO EM EVENTOS
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_events AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(pe.id))[1] AS canonical_id,
            ARRAY_AGG(pe.id) AS production_ids,
            ARRAY_AGG(DISTINCT pe.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            pe.title,
            pe.event_name,
            pe.year,
            MAX(pe.nature) AS nature,
            MAX(pe.type_participation) AS type_participation,
            MAX(pe.form_participation) AS form_participation
        FROM participation_events pe
        LEFT JOIN researcher r ON r.id = pe.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = pe.researcher_id
        GROUP BY
            COALESCE(NULLIF(LOWER(TRIM(pe.title)), ''), LOWER(UNACCENT(TRIM(pe.event_name)))) || '_' || COALESCE(pe.year::text, ''),
            pe.title,
            pe.event_name,
            pe.year
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        platform_authors,
        title,
        event_name,
        year,
        nature,
        type_participation,
        form_participation,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(event_name, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(nature, '') || ' ' || coalesce(type_participation, '')), 'C')
        ) AS search_vector
    FROM deduplicated;
    """)

    # 7. PROJETOS DE PESQUISA
    op.execute("""
    CREATE MATERIALIZED VIEW mv_canonical_research_projects AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(rp.id ORDER BY rp.id))[1] AS canonical_id,
            ARRAY_AGG(DISTINCT rp.id) AS production_ids,
            ARRAY_AGG(DISTINCT rp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            MAX(rp.project_name) AS title,
            rp.start_year,
            MAX(rp.end_year) AS end_year,
            MAX(rp.status) AS status,
            MAX(rp.nature) AS nature,
            MAX(rp.agency_name) AS agency_name,
            MAX(rp.agency_code) AS agency_code,
            MAX(rp.description) AS description,
            MAX(rp.number_undergraduates) AS number_undergraduates,
            MAX(rp.number_specialists) AS number_specialists,
            MAX(rp.number_academic_masters) AS number_academic_masters,
            MAX(rp.number_phd) AS number_phd
        FROM research_project rp
        LEFT JOIN researcher r ON r.id = rp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = rp.researcher_id
        WHERE NULLIF(TRIM(rp.project_name), '') IS NOT NULL
        GROUP BY
            LOWER(UNACCENT(TRIM(rp.project_name))),
            rp.start_year
    )
    SELECT
        d.canonical_id,
        d.production_ids,
        d.researcher_ids,
        d.institution_ids,
        d.graduate_program_ids,
        d.platform_authors,
        d.title,
        d.start_year AS year,
        d.start_year,
        d.end_year,
        d.status,
        d.nature,
        d.agency_name,
        d.agency_code,
        d.description,
        d.number_undergraduates,
        d.number_specialists,
        d.number_academic_masters,
        d.number_phd,
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'agency_name', f.agency_name,
                'agency_code', f.agency_code,
                'nature', f.nature
            ))
            FROM research_project_foment f
            WHERE f.project_id = ANY(d.production_ids)
        ) AS foment,
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'name', c.name,
                'lattes_id', c.lattes_id,
                'citations', c.citations,
                'coordinator', c.coordinator
            ))
            FROM research_project_components c
            WHERE c.project_id = ANY(d.production_ids)
        ) AS components,
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'title', p.title,
                'type', p.type
            ))
            FROM research_project_production p
            WHERE p.project_id = ANY(d.production_ids)
        ) AS productions,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(d.title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(d.description, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(d.agency_name, '') || ' ' || coalesce(d.nature, '')), 'C')
        ) AS search_vector
    FROM deduplicated d;
    """)

    for idx in COMMON_INDEXES:
        op.execute(idx)
