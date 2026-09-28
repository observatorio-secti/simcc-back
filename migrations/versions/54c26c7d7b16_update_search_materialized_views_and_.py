"""update_search_materialized_views_and_add_documents_mv

Revision ID: 54c26c7d7b16
Revises: e7796887be76
Create Date: 2026-09-25 09:53:59.270706

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '54c26c7d7b16'
down_revision: Union[str, Sequence[str], None] = 'e7796887be76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Dropar mv_researcher_search legada (Camada 2 antiga com combined_vector)
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;')

    # 2. Criar mv_search_documents (Camada 1 consolidada: UNION ALL das 4 fontes)
    op.execute("""
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
    """)

    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_docs_pk '
        'ON mv_search_documents (source_type, source_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_researcher '
        'ON mv_search_documents (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_vector '
        'ON mv_search_documents USING GIN (search_vector);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_year_researcher '
        'ON mv_search_documents (year_, researcher_id);'
    )

    # 3. Recriar mv_researcher_search (Camada 2 com profile_vector e institution_ids)
    op.execute("""
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
            array_agg(DISTINCT inst_id) FILTER (WHERE inst_id IS NOT NULL) AS institution_ids
        FROM all_inst
        GROUP BY researcher_id
    ),
    years_agg AS (
        SELECT
            researcher_id,
            array_agg(DISTINCT year_) FILTER (WHERE year_ IS NOT NULL) AS production_years
        FROM mv_search_documents
        GROUP BY researcher_id
    ),
    gp_agg AS (
        SELECT
            researcher_id,
            array_agg(DISTINCT graduate_program_id) FILTER (WHERE graduate_program_id IS NOT NULL) AS graduate_program_ids
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
            setweight(to_tsvector('pt_unaccent', coalesce(r.name, '')), 'A') ||
            setweight(to_tsvector('pt_unaccent', coalesce(r.abstract, '')), 'C')
        ) AS profile_vector
    FROM researcher r
    LEFT JOIN institution inst ON inst.id = r.institution_id
    LEFT JOIN inst_agg ia ON ia.researcher_id = r.id
    LEFT JOIN gp_agg gp ON gp.researcher_id = r.id
    LEFT JOIN years_agg ya ON ya.researcher_id = r.id;
    """)

    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_researcher_id '
        'ON mv_researcher_search (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_profile_vector '
        'ON mv_researcher_search USING GIN (profile_vector);'
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
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_institution_ids '
        'ON mv_researcher_search USING GIN (institution_ids);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_gp_ids '
        'ON mv_researcher_search USING GIN (graduate_program_ids);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_production_years '
        'ON mv_researcher_search USING GIN (production_years);'
    )

    # 4. Tabela de metadados para tracking do refresh
    op.execute("""
    CREATE TABLE IF NOT EXISTS mv_refresh_metadata (
        view_name TEXT PRIMARY KEY,
        refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        duration_ms INTEGER
    );
    """)


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS mv_refresh_metadata CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_search_documents CASCADE;')
