"""researcher_search_mv_affiliations_and_counts

Recria mv_researcher_search usando apenas researcher_institution para os
vínculos institucionais (abandonando researcher.institution_id) e
incluindo os campos do card de pesquisador (formação, classificação,
atualização do Lattes e contadores de produção).

Revision ID: 3f6c2a91d7e4
Revises: 54c26c7d7b16
Create Date: 2026-09-25 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3f6c2a91d7e4'
down_revision: Union[str, Sequence[str], None] = '54c26c7d7b16'
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


def upgrade() -> None:
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


def downgrade() -> None:
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search;')
    op.execute("""
    CREATE MATERIALIZED VIEW mv_researcher_search AS
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
    for stmt in COMMON_INDEXES:
        op.execute(stmt)
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_researcher_institution_id '
        'ON mv_researcher_search (institution_id);'
    )
