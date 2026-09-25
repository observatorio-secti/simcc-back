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
    FROM mv_search_software;
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
    WITH all_inst AS (
        SELECT id AS researcher_id, institution_id AS inst_id
        FROM researcher
        WHERE institution_id IS NOT NULL
        UNION
        SELECT researcher_id, institution_id AS inst_id
        FROM researcher_institution
        WHERE institution_id IS NOT NULL
    ),
    inst_agg AS (
        SELECT
            researcher_id,
            array_agg(DISTINCT inst_id)
                FILTER (WHERE inst_id IS NOT NULL) AS institution_ids
        FROM all_inst
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
        r.institution_id,
        inst.name AS institution_name,
        inst.acronym AS institution_acronym,
        coalesce(ia.institution_ids, '{}') AS institution_ids,
        coalesce(gp.graduate_program_ids, '{}') AS graduate_program_ids,
        coalesce(ya.production_years, '{}') AS production_years,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(r.name, '')), 'A')
            || setweight(
                to_tsvector('pt_unaccent', coalesce(r.abstract, '')), 'C'
            )
        ) AS profile_vector
    FROM researcher r
    LEFT JOIN institution inst ON inst.id = r.institution_id
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
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_institution_id '
        'ON mv_researcher_search (institution_id);'
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
    CREATE TABLE IF NOT EXISTS mv_refresh_metadata (
        view_name TEXT PRIMARY KEY,
        refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        duration_ms INTEGER
    );
    """,
]

TEARDOWN_MVS_STATEMENTS = [
    'DROP TABLE IF EXISTS mv_refresh_metadata CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;',
    'DROP MATERIALIZED VIEW IF EXISTS mv_search_documents CASCADE;',
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
