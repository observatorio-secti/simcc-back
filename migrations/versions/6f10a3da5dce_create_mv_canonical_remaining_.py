"""create_mv_canonical_remaining_productions

Revision ID: 6f10a3da5dce
Revises: 0cc7a77e8067
Create Date: 2026-10-02 10:44:20.480658

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f10a3da5dce'
down_revision: Union[str, Sequence[str], None] = '0cc7a77e8067'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. LIVROS
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_books AS
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

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_books_pk ON mv_canonical_books (canonical_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_isbn ON mv_canonical_books (isbn);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_year ON mv_canonical_books (year DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_researchers ON mv_canonical_books USING GIN (researcher_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_institutions ON mv_canonical_books USING GIN (institution_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_programs ON mv_canonical_books USING GIN (graduate_program_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_prods ON mv_canonical_books USING GIN (production_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_books_vector ON mv_canonical_books USING GIN (search_vector);")

    # 2. CAPÍTULOS DE LIVROS
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_book_chapters AS
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

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_chapters_pk ON mv_canonical_book_chapters (canonical_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_isbn ON mv_canonical_book_chapters (isbn);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_year ON mv_canonical_book_chapters (year DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_researchers ON mv_canonical_book_chapters USING GIN (researcher_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_institutions ON mv_canonical_book_chapters USING GIN (institution_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_programs ON mv_canonical_book_chapters USING GIN (graduate_program_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_prods ON mv_canonical_book_chapters USING GIN (production_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_chapters_vector ON mv_canonical_book_chapters USING GIN (search_vector);")

    # 3. SOFTWARES
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_software AS
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

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_software_pk ON mv_canonical_software (canonical_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_code ON mv_canonical_software (code);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_year ON mv_canonical_software (year DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_researchers ON mv_canonical_software USING GIN (researcher_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_institutions ON mv_canonical_software USING GIN (institution_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_programs ON mv_canonical_software USING GIN (graduate_program_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_prods ON mv_canonical_software USING GIN (production_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_software_vector ON mv_canonical_software USING GIN (search_vector);")

    # 4. PATENTES
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_patents AS
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

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_patents_pk ON mv_canonical_patents (canonical_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_code ON mv_canonical_patents (code);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_year ON mv_canonical_patents (year DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_researchers ON mv_canonical_patents USING GIN (researcher_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_institutions ON mv_canonical_patents USING GIN (institution_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_programs ON mv_canonical_patents USING GIN (graduate_program_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_prods ON mv_canonical_patents USING GIN (production_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_patents_vector ON mv_canonical_patents USING GIN (search_vector);")

    # 5. PARTICIPAÇÃO EM EVENTOS
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_events AS
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

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_events_pk ON mv_canonical_events (canonical_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_year ON mv_canonical_events (year DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_researchers ON mv_canonical_events USING GIN (researcher_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_institutions ON mv_canonical_events USING GIN (institution_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_programs ON mv_canonical_events USING GIN (graduate_program_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_prods ON mv_canonical_events USING GIN (production_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_events_vector ON mv_canonical_events USING GIN (search_vector);")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_canonical_events CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_canonical_patents CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_canonical_software CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_canonical_book_chapters CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_canonical_books CASCADE;")
