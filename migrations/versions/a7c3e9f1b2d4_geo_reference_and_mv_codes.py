# ruff: noqa: E501
"""geo reference tables and territory/IBGE codes in mv_researcher_search

Cria `identity_territory` (código SEI 1 a 27) e `municipality` (código
IBGE), acrescenta `city.ibge_code` e recria `mv_researcher_search` com
`ibge_codes` e `territory_codes`, derivados da cidade de cada vínculo.
Os dados das tabelas de referência vêm da rotina `seed_geo_reference` do
simcc-etl.

Revision ID: a7c3e9f1b2d4
Revises: f1a2b3c4d5e6
Create Date: 2026-11-22 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = 'a7c3e9f1b2d4'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEXES = [
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
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_collection_slugs ON mv_researcher_search USING GIN (collection_slugs);',
]
GEO_INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_ibge_codes ON mv_researcher_search USING GIN (ibge_codes);',
    'CREATE INDEX IF NOT EXISTS idx_mv_researcher_territory_codes ON mv_researcher_search USING GIN (territory_codes);',
]


def mv_sql(with_geo: bool) -> str:
    geo_cte = (
        """
    geo_agg AS (
        SELECT
            ri.researcher_id,
            array_agg(DISTINCT c.ibge_code::text)
                FILTER (WHERE c.ibge_code IS NOT NULL) AS ibge_codes,
            array_agg(DISTINCT m.territory_code)
                FILTER (WHERE m.territory_code IS NOT NULL)
                AS territory_codes
        FROM researcher_institution ri
        JOIN city c ON c.id = ri.city_id
        LEFT JOIN municipality m ON m.ibge_code = c.ibge_code
        GROUP BY ri.researcher_id
    ),"""
        if with_geo
        else ''
    )
    geo_cols = (
        """
        coalesce(ga.ibge_codes, '{}') AS ibge_codes,
        coalesce(ga.territory_codes, '{}') AS territory_codes,"""
        if with_geo
        else ''
    )
    geo_join = (
        '\n    LEFT JOIN geo_agg ga ON ga.researcher_id = r.id' if with_geo else ''
    )
    return f"""
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
    ),{geo_cte}
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
        coalesce(ia.institution_ids, '{{}}') AS institution_ids,
        coalesce(ia.city_ids, '{{}}') AS city_ids,
        coalesce(ia.identity_territories, '{{}}') AS identity_territories,{geo_cols}
        coalesce(gp.graduate_program_ids, '{{}}') AS graduate_program_ids,
        coalesce(ya.production_years, '{{}}') AS production_years,
        coalesce(ca.collection_slugs, '{{}}') AS collection_slugs,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(r.name, '')), 'A')
            || setweight(
                to_tsvector('pt_unaccent', coalesce(r.abstract, '')), 'C'
            )
        ) AS profile_vector
    FROM researcher r
    LEFT JOIN researcher_production rp ON rp.researcher_id = r.id
    LEFT JOIN inst_agg ia ON ia.researcher_id = r.id{geo_join}
    LEFT JOIN gp_agg gp ON gp.researcher_id = r.id
    LEFT JOIN years_agg ya ON ya.researcher_id = r.id
    LEFT JOIN coll_agg ca ON ca.researcher_id = r.id;
    """


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS identity_territory (
        code SMALLINT PRIMARY KEY,
        name VARCHAR NOT NULL UNIQUE,
        slug VARCHAR NOT NULL UNIQUE
    );
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS municipality (
        ibge_code CHAR(7) PRIMARY KEY,
        name VARCHAR NOT NULL,
        uf CHAR(2) NOT NULL,
        territory_code SMALLINT REFERENCES identity_territory(code)
    );
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_municipality_territory_code '
        'ON municipality (territory_code);'
    )
    op.execute(
        'ALTER TABLE city ADD COLUMN IF NOT EXISTS ibge_code CHAR(7) '
        'REFERENCES municipality(ibge_code) ON DELETE SET NULL;'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_city_ibge_code ON city (ibge_code);'
    )

    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;')
    op.execute(mv_sql(with_geo=True))
    for idx in INDEXES + GEO_INDEXES:
        op.execute(idx)


def downgrade() -> None:
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_researcher_search CASCADE;')
    op.execute(mv_sql(with_geo=False))
    for idx in INDEXES:
        op.execute(idx)

    op.execute('DROP INDEX IF EXISTS idx_city_ibge_code;')
    op.execute('ALTER TABLE city DROP COLUMN IF EXISTS ibge_code;')
    op.execute('DROP TABLE IF EXISTS municipality;')
    op.execute('DROP TABLE IF EXISTS identity_territory;')
