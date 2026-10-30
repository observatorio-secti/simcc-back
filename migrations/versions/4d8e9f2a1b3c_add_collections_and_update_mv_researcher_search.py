"""add_collections_and_update_mv_researcher_search

Revision ID: 4d8e9f2a1b3c
Revises: 3c5e8a1f2b7d
Create Date: 2026-10-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4d8e9f2a1b3c'
down_revision: Union[str, Sequence[str], None] = '3c5e8a1f2b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COMMON_INDEXES_V1 = [
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

COMMON_INDEXES_V2 = COMMON_INDEXES_V1 + [
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_collection_slugs ON mv_researcher_search USING GIN (collection_slugs);',
]


def upgrade() -> None:
    # 1. Criar tabelas collection e researcher_collection
    op.execute("""
    CREATE TABLE IF NOT EXISTS collection (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        slug VARCHAR NOT NULL UNIQUE,
        name VARCHAR NOT NULL UNIQUE,
        description TEXT,
        refresh_interval_days INTEGER NOT NULL DEFAULT 1,
        is_default BOOLEAN NOT NULL DEFAULT false,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS researcher_collection (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        researcher_id UUID NOT NULL REFERENCES researcher(id) ON DELETE CASCADE,
        collection_id UUID NOT NULL REFERENCES collection(id) ON DELETE CASCADE,
        attributes JSONB,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT uq_researcher_collection UNIQUE (researcher_id, collection_id)
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_researcher_collection_researcher_id ON researcher_collection (researcher_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_researcher_collection_collection_id ON researcher_collection (collection_id);")

    # Inserir coleção default 'simcc' e vincular pesquisadores existentes
    op.execute("""
    INSERT INTO collection (slug, name, description, refresh_interval_days, is_default)
    VALUES ('simcc', 'SimCC', 'Coleção principal da plataforma SimCC', 1, true)
    ON CONFLICT (slug) DO NOTHING;
    """)

    op.execute("""
    INSERT INTO researcher_collection (researcher_id, collection_id)
    SELECT r.id, c.id
    FROM researcher r
    CROSS JOIN collection c
    WHERE c.slug = 'simcc'
    ON CONFLICT (researcher_id, collection_id) DO NOTHING;
    """)

    # 2. Recriar mv_researcher_search com collection_slugs
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;')

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
    ),
    coll_agg AS (
        SELECT
            rc.researcher_id,
            array_agg(DISTINCT c.slug)
                FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs
        FROM researcher_collection rc
        JOIN collection c ON c.id = rc.collection_id
        GROUP BY rc.researcher_id
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
        coalesce(ca.collection_slugs, '{}') AS collection_slugs,
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
    LEFT JOIN years_agg ya ON ya.researcher_id = r.id
    LEFT JOIN coll_agg ca ON ca.researcher_id = r.id;
    """)

    for idx in COMMON_INDEXES_V2:
        op.execute(idx)


def downgrade() -> None:
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;')

    # Recriar mv_researcher_search anterior (sem collection_slugs)
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

    for idx in COMMON_INDEXES_V1:
        op.execute(idx)

    op.execute('DROP TABLE IF EXISTS researcher_collection CASCADE;')
    op.execute('DROP TABLE IF EXISTS collection CASCADE;')
