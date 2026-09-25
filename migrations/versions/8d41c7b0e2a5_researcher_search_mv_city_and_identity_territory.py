"""researcher_search_mv_city_and_identity_territory

Adiciona à mv_researcher_search os arrays `city_ids` e
`identity_territories`, vindos de researcher_institution, para os filtros
e facets de cidade e território de identidade da v2.

Revision ID: 8d41c7b0e2a5
Revises: 3f6c2a91d7e4
Create Date: 2026-09-25 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8d41c7b0e2a5'
down_revision: Union[str, Sequence[str], None] = '3f6c2a91d7e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COMMON_INDEXES = [
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_researcher_id '
    'ON mv_researcher_search (researcher_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_profile_vector '
    'ON mv_researcher_search USING GIN (profile_vector);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_name_trgm '
    'ON mv_researcher_search USING GIN (name gin_trgm_ops);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_institution_ids '
    'ON mv_researcher_search USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_gp_ids '
    'ON mv_researcher_search USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_production_years '
    'ON mv_researcher_search USING GIN (production_years);',
]

NEW_INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_city_ids '
    'ON mv_researcher_search USING GIN (city_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_identity_territories '
    'ON mv_researcher_search USING GIN (identity_territories);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_graduation '
    'ON mv_researcher_search (graduation);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_classification '
    'ON mv_researcher_search (classification);',
]


def upgrade() -> None:
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search;')
    op.execute("""
    CREATE MATERIALIZED VIEW mv_researcher_search AS
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
    """)
    for stmt in COMMON_INDEXES + NEW_INDEXES:
        op.execute(stmt)


def downgrade() -> None:
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search;')
    op.execute("""
    CREATE MATERIALIZED VIEW mv_researcher_search AS
    WITH inst_agg AS (
        SELECT
            researcher_id,
            array_agg(DISTINCT institution_id) AS institution_ids
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
    """)
    for stmt in COMMON_INDEXES:
        op.execute(stmt)
