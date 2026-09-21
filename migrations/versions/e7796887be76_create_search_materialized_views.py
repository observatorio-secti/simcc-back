"""create_search_materialized_views

Revision ID: e7796887be76
Revises: 9b38fbff8df4
Create Date: 2026-09-21 15:54:25.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e7796887be76'
down_revision: Union[str, Sequence[str], None] = '9b38fbff8df4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Extensões e Configuração de busca textual
    op.execute('CREATE EXTENSION IF NOT EXISTS unaccent;')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')

    op.execute("""
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
    """)

    # 1. Camada 1: MVs por fonte
    # 1.1 Articles
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_articles AS
    SELECT
        bp.researcher_id,
        bp.id AS source_id,
        'ARTICLE'::text AS source_type,
        bp.title,
        bp.year_,
        oa.abstract,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(bp.title, '')), 'B') ||
            setweight(to_tsvector('pt_unaccent', coalesce(oa.keywords, '')), 'C') ||
            setweight(to_tsvector('pt_unaccent', coalesce(oa.abstract, '')), 'D')
        ) AS search_vector
    FROM bibliographic_production bp
    LEFT JOIN openalex_article oa ON oa.article_id = bp.id
    WHERE bp.type = 'ARTICLE';
    """)
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_articles_pk '
        'ON mv_search_articles (source_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_articles_researcher '
        'ON mv_search_articles (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_articles_vector '
        'ON mv_search_articles USING GIN (search_vector);'
    )

    # 1.2 Books & Chapters
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_books AS
    SELECT
        bp.researcher_id,
        bp.id AS source_id,
        bp.type::text AS source_type,
        bp.title,
        bp.year_,
        NULL::text AS abstract,
        setweight(to_tsvector('pt_unaccent', coalesce(bp.title, '')), 'B') AS search_vector
    FROM bibliographic_production bp
    WHERE bp.type IN ('BOOK', 'BOOK_CHAPTER');
    """)
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_books_pk '
        'ON mv_search_books (source_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_books_researcher '
        'ON mv_search_books (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_books_vector '
        'ON mv_search_books USING GIN (search_vector);'
    )

    # 1.3 Patents
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_patents AS
    SELECT
        p.researcher_id,
        p.id AS source_id,
        'PATENT'::text AS source_type,
        p.title,
        NULLIF(regexp_replace(p.development_year, '\\D', '', 'g'), '')::int AS year_,
        NULL::text AS abstract,
        setweight(to_tsvector('pt_unaccent', coalesce(p.title, '')), 'B') AS search_vector
    FROM patent p;
    """)
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_patents_pk '
        'ON mv_search_patents (source_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_patents_researcher '
        'ON mv_search_patents (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_patents_vector '
        'ON mv_search_patents USING GIN (search_vector);'
    )

    # 1.4 Software
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_software AS
    SELECT
        s.researcher_id,
        s.id AS source_id,
        'SOFTWARE'::text AS source_type,
        s.title,
        s.year AS year_,
        NULL::text AS abstract,
        setweight(to_tsvector('pt_unaccent', coalesce(s.title, '')), 'B') AS search_vector
    FROM software s;
    """)
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_software_pk '
        'ON mv_search_software (source_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_software_researcher '
        'ON mv_search_software (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_software_vector '
        'ON mv_search_software USING GIN (search_vector);'
    )

    # 2. Camada 2: MV agregada mv_researcher_search
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_researcher_search AS
    WITH all_sources AS (
        SELECT researcher_id, source_type, title, year_, search_vector FROM mv_search_articles
        UNION ALL
        SELECT researcher_id, source_type, title, year_, search_vector FROM mv_search_books
        UNION ALL
        SELECT researcher_id, source_type, title, year_, search_vector FROM mv_search_patents
        UNION ALL
        SELECT researcher_id, source_type, title, year_, search_vector FROM mv_search_software
    ),
    sources_agg AS (
        SELECT
            researcher_id,
            string_agg(search_vector::text, ' ')::tsvector AS combined_vector,
            array_agg(DISTINCT year_) FILTER (WHERE year_ IS NOT NULL) AS production_years
        FROM all_sources
        GROUP BY researcher_id
    ),
    gp_agg AS (
        SELECT researcher_id, array_agg(DISTINCT graduate_program_id) AS graduate_program_ids
        FROM graduate_program_researcher
        GROUP BY researcher_id
    )
    SELECT
        r.id AS researcher_id,
        r.name,
        r.institution_id,
        inst.name AS institution_name,
        inst.acronym AS institution_acronym,
        coalesce(gp.graduate_program_ids, '{}') AS graduate_program_ids,
        coalesce(src.production_years, '{}') AS production_years,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(r.name, '')), 'A') ||
            setweight(to_tsvector('pt_unaccent', coalesce(r.abstract, '')), 'C') ||
            coalesce(src.combined_vector, ''::tsvector)
        ) AS search_vector
    FROM researcher r
    LEFT JOIN institution inst ON inst.id = r.institution_id
    LEFT JOIN sources_agg src ON src.researcher_id = r.id
    LEFT JOIN gp_agg gp ON gp.researcher_id = r.id
    WHERE r.status = TRUE;
    """)
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_researcher_id '
        'ON mv_researcher_search (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_search_vector '
        'ON mv_researcher_search USING GIN (search_vector);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_name_trgm '
        'ON mv_researcher_search USING GIN (name gin_trgm_ops);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_institution_id '
        'ON mv_researcher_search (institution_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_gp_ids '
        'ON mv_researcher_search USING GIN (graduate_program_ids);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_production_years '
        'ON mv_researcher_search USING GIN (production_years);'
    )


def downgrade() -> None:
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_search_software CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_search_patents CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_search_books CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_search_articles CASCADE;')
    op.execute('DROP TEXT SEARCH CONFIGURATION IF EXISTS pt_unaccent CASCADE;')
