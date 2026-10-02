"""Helper para inicialização de visões materializadas de busca nos testes."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

SETUP_MVS_STATEMENTS = [
    'CREATE EXTENSION IF NOT EXISTS unaccent;',
    'CREATE EXTENSION IF NOT EXISTS pg_trgm;',
    """
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_ts_config WHERE cfgname = 'pt_unaccent'
      ) THEN
        CREATE TEXT SEARCH CONFIGURATION pt_unaccent ( COPY = portuguese );
        ALTER TEXT SEARCH CONFIGURATION pt_unaccent
          ALTER MAPPING FOR hword, hword_part, word
          WITH unaccent, portuguese_stem;
      END IF;
    END
    $$;
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_articles AS
    SELECT
        bp.researcher_id,
        bp.id AS source_id,
        'ARTICLE'::text AS source_type,
        bp.title,
        bp.year_,
        oa.abstract,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(bp.title, '')), 'B')
            || setweight(
                to_tsvector('pt_unaccent', coalesce(oa.keywords, '')), 'C'
            )
            || setweight(
                to_tsvector('pt_unaccent', coalesce(oa.abstract, '')), 'D'
            )
        ) AS search_vector
    FROM bibliographic_production bp
    LEFT JOIN openalex_article oa ON oa.article_id = bp.id
    WHERE bp.type = 'ARTICLE';
    """,
    (
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_articles_pk '
        'ON mv_search_articles (source_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_articles_researcher '
        'ON mv_search_articles (researcher_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_articles_vector '
        'ON mv_search_articles USING GIN (search_vector);'
    ),
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_books AS
    SELECT
        bp.researcher_id,
        bp.id AS source_id,
        bp.type::text AS source_type,
        bp.title,
        bp.year_,
        NULL::text AS abstract,
        setweight(
            to_tsvector('pt_unaccent', coalesce(bp.title, '')), 'B'
        ) AS search_vector
    FROM bibliographic_production bp
    WHERE bp.type IN ('BOOK', 'BOOK_CHAPTER');
    """,
    (
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_books_pk '
        'ON mv_search_books (source_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_books_researcher '
        'ON mv_search_books (researcher_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_books_vector '
        'ON mv_search_books USING GIN (search_vector);'
    ),
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_patents AS
    SELECT
        p.researcher_id,
        p.id AS source_id,
        'PATENT'::text AS source_type,
        p.title,
        CASE
            WHEN p.development_year ~ '^[0-9]+$'
            THEN p.development_year::int
            ELSE NULL
        END AS year_,
        NULL::text AS abstract,
        setweight(
            to_tsvector('pt_unaccent', coalesce(p.title, '')), 'B'
        ) AS search_vector
    FROM patent p;
    """,
    (
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_patents_pk '
        'ON mv_search_patents (source_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_patents_researcher '
        'ON mv_search_patents (researcher_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_patents_vector '
        'ON mv_search_patents USING GIN (search_vector);'
    ),
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_software AS
    SELECT
        s.researcher_id,
        s.id AS source_id,
        'SOFTWARE'::text AS source_type,
        s.title,
        s.year AS year_,
        NULL::text AS abstract,
        setweight(
            to_tsvector('pt_unaccent', coalesce(s.title, '')), 'B'
        ) AS search_vector
    FROM software s;
    """,
    (
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_software_pk '
        'ON mv_search_software (source_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_software_researcher '
        'ON mv_search_software (researcher_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_software_vector '
        'ON mv_search_software USING GIN (search_vector);'
    ),
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_events AS
    SELECT
        pe.researcher_id,
        pe.id AS source_id,
        'PARTICIPATION_EVENT'::text AS source_type,
        coalesce(pe.event_name, pe.title, '') AS title,
        pe.year AS year_,
        NULL::text AS abstract,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(pe.event_name, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(pe.title, '')), 'C')
        ) AS search_vector
    FROM participation_events pe;
    """,
    (
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_events_pk '
        'ON mv_search_events (source_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_events_researcher '
        'ON mv_search_events (researcher_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_events_vector '
        'ON mv_search_events USING GIN (search_vector);'
    ),
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_areas AS
    SELECT
        rae.researcher_id,
        rae.id AS source_id,
        'AREA_SPECIALTY'::text AS source_type,
        replace(coalesce(asp.name, ''), '_', ' ') AS title,
        NULL::integer AS year_,
        NULL::text AS abstract,
        setweight(
            to_tsvector('pt_unaccent', replace(coalesce(asp.name, ''), '_', ' ')), 'A'
        ) AS search_vector
    FROM researcher_area_expertise rae
    JOIN area_specialty asp ON asp.id = rae.area_specialty_id;
    """,
    (
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_areas_pk '
        'ON mv_search_areas (source_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_areas_researcher '
        'ON mv_search_areas (researcher_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_areas_vector '
        'ON mv_search_areas USING GIN (search_vector);'
    ),
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_documents AS
    SELECT researcher_id, source_id, source_type, title, year_, search_vector
    FROM mv_search_articles
    UNION ALL
    SELECT researcher_id, source_id, source_type, title, year_, search_vector
    FROM mv_search_books
    UNION ALL
    SELECT researcher_id, source_id, source_type, title, year_, search_vector
    FROM mv_search_patents
    UNION ALL
    SELECT researcher_id, source_id, source_type, title, year_, search_vector
    FROM mv_search_software
    UNION ALL
    SELECT researcher_id, source_id, source_type, title, year_, search_vector
    FROM mv_search_events
    UNION ALL
    SELECT researcher_id, source_id, source_type, title, year_, search_vector
    FROM mv_search_areas;
    """,
    (
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_docs_pk '
        'ON mv_search_documents (source_type, source_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_researcher '
        'ON mv_search_documents (researcher_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_vector '
        'ON mv_search_documents USING GIN (search_vector);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_year_researcher '
        'ON mv_search_documents (year_, researcher_id);'
    ),
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_researcher_search AS
    WITH inst_agg AS (
        SELECT
            researcher_id,
            array_agg(DISTINCT institution_id) AS institution_ids,
            array_agg(DISTINCT city_id)
                FILTER (WHERE city_id IS NOT NULL) AS city_ids,
            array_agg(DISTINCT identity_territory)
                FILTER (WHERE identity_territory IS NOT NULL)
                AS identity_territories
        FROM researcher_institution
        GROUP BY researcher_id
    ),
    years_agg AS (
        SELECT
            researcher_id,
            array_agg(DISTINCT year_)
                FILTER (WHERE year_ IS NOT NULL) AS production_years
        FROM mv_search_documents
        GROUP BY researcher_id
    ),
    gp_agg AS (
        SELECT
            researcher_id,
            array_agg(DISTINCT graduate_program_id)
                FILTER (WHERE graduate_program_id IS NOT NULL)
                AS graduate_program_ids
        FROM graduate_program_researcher
        GROUP BY researcher_id
    )
    SELECT
        r.id AS researcher_id,
        r.name,
        r.graduation,
        r.classification,
        r.last_update AS lattes_update,
        coalesce(rp.articles, 0) AS articles,
        coalesce(rp.book_chapters, 0) AS book_chapters,
        coalesce(rp.book, 0) AS books,
        coalesce(rp.patent, 0) AS patents,
        coalesce(rp.software, 0) AS software,
        coalesce(rp.brand, 0) AS brands,
        coalesce(ia.institution_ids, '{}') AS institution_ids,
        coalesce(ia.city_ids, '{}') AS city_ids,
        coalesce(ia.identity_territories, '{}') AS identity_territories,
        coalesce(gp.graduate_program_ids, '{}') AS graduate_program_ids,
        coalesce(ya.production_years, '{}') AS production_years,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(r.name, '')), 'A')
            || setweight(
                to_tsvector('pt_unaccent', coalesce(r.abstract, '')), 'C'
            )
        ) AS profile_vector
    FROM researcher r
    LEFT JOIN researcher_production rp ON rp.researcher_id = r.id
    LEFT JOIN inst_agg ia ON ia.researcher_id = r.id
    LEFT JOIN gp_agg gp ON gp.researcher_id = r.id
    LEFT JOIN years_agg ya ON ya.researcher_id = r.id;
    """,
    (
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_researcher_id '
        'ON mv_researcher_search (researcher_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_profile_vector '
        'ON mv_researcher_search USING GIN (profile_vector);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_name_trgm '
        'ON mv_researcher_search USING GIN (name gin_trgm_ops);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_institution_ids '
        'ON mv_researcher_search USING GIN (institution_ids);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_gp_ids '
        'ON mv_researcher_search USING GIN (graduate_program_ids);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_production_years '
        'ON mv_researcher_search USING GIN (production_years);'
    ),
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_articles AS
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
    """,
    (
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_articles_pk '
        'ON mv_canonical_articles (canonical_id);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_doi '
        'ON mv_canonical_articles (doi);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_year '
        'ON mv_canonical_articles (year DESC);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_citations '
        'ON mv_canonical_articles (citations_count DESC);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_qualis '
        'ON mv_canonical_articles (qualis);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_researchers '
        'ON mv_canonical_articles USING GIN (researcher_ids);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_institutions '
        'ON mv_canonical_articles USING GIN (institution_ids);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_programs '
        'ON mv_canonical_articles USING GIN (graduate_program_ids);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_prods '
        'ON mv_canonical_articles USING GIN (production_ids);'
    ),
    (
        'CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_vector '
        'ON mv_canonical_articles USING GIN (search_vector);'
    ),
    """
    CREATE TABLE IF NOT EXISTS mv_refresh_metadata (
        view_name TEXT PRIMARY KEY,
        refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        duration_ms INTEGER
    );
    """,
]

TEARDOWN_MVS_STATEMENTS = [
    'DROP TABLE IF EXISTS mv_refresh_metadata CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_canonical_articles CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_search_documents CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_search_areas CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_search_events CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_search_software CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_search_patents CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_search_books CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_search_articles CASCADE;',
]


async def init_test_mvs(conn: AsyncConnection) -> None:
    """Executa os comandos de criação das MVs no banco de testes."""
    for stmt in SETUP_MVS_STATEMENTS:
        cleaned = stmt.strip()
        if cleaned:
            await conn.execute(text(cleaned))


async def drop_test_mvs(conn: AsyncConnection) -> None:
    """Remove as MVs do banco de testes."""
    for stmt in TEARDOWN_MVS_STATEMENTS:
        cleaned = stmt.strip()
        if cleaned:
            await conn.execute(text(cleaned))
