# ruff: noqa: E501
"""add_events_and_areas_to_search_materialized_views

Adiciona mv_search_events (participação em eventos) e mv_search_areas (área de especialidade)
à Camada 1 e as consolida em mv_search_documents, permitindo filtragem e busca textual
por PARTICIPATION_EVENT e AREA_SPECIALTY na v2.

Revision ID: 8ae74128eb49
Revises: 0e4fe6912053
Create Date: 2026-10-02 00:05:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8ae74128eb49'
down_revision: Union[str, Sequence[str], None] = '0e4fe6912053'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COMMON_INDEXES = [
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_researcher_id ON mv_researcher_search (researcher_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_profile_vector ON mv_researcher_search USING GIN (profile_vector);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_name_trgm ON mv_researcher_search USING GIN (name gin_trgm_ops);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_institution_ids ON mv_researcher_search USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_gp_ids ON mv_researcher_search USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_production_years ON mv_researcher_search USING GIN (production_years);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_city_ids ON mv_researcher_search USING GIN (city_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_identity_territories ON mv_researcher_search USING GIN (identity_territories);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_graduation ON mv_researcher_search (graduation);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_classification ON mv_researcher_search (classification);',
]


def upgrade() -> None:
    # 1. Dropar dependentes
    op.execute(
        'DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;'
    )
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_search_documents CASCADE;')

    # 2. Criar mv_search_events
    op.execute("""
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
    """)
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_events_pk ON mv_search_events (source_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_events_researcher ON mv_search_events (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_events_vector ON mv_search_events USING GIN (search_vector);'
    )

    # 3. Criar mv_search_areas
    op.execute("""
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
    """)
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_areas_pk ON mv_search_areas (source_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_areas_researcher ON mv_search_areas (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_areas_vector ON mv_search_areas USING GIN (search_vector);'
    )

    # 4. Criar mv_search_documents (6 fontes)
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
    FROM mv_search_software
    UNION ALL
    SELECT researcher_id, source_id, source_type, title, year_, search_vector
    FROM mv_search_events
    UNION ALL
    SELECT researcher_id, source_id, source_type, title, year_, search_vector
    FROM mv_search_areas;
    """)
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_docs_pk ON mv_search_documents (source_type, source_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_researcher ON mv_search_documents (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_vector ON mv_search_documents USING GIN (search_vector);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_year_researcher ON mv_search_documents (year_, researcher_id);'
    )

    # 5. Recriar mv_researcher_search
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

    for idx in COMMON_INDEXES:
        op.execute(idx)


def downgrade() -> None:
    op.execute(
        'DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;'
    )
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_search_documents CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_search_areas CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_search_events CASCADE;')

    # Recriar mv_search_documents com as 4 fontes originais
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
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_docs_pk ON mv_search_documents (source_type, source_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_researcher ON mv_search_documents (researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_vector ON mv_search_documents USING GIN (search_vector);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_mv_search_docs_year_researcher ON mv_search_documents (year_, researcher_id);'
    )

    # Recriar mv_researcher_search
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

    for idx in COMMON_INDEXES:
        op.execute(idx)
