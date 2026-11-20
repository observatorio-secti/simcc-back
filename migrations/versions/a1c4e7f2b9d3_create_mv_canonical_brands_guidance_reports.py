# ruff: noqa: E501, W291, W293
"""create mv_canonical brands, guidance and reports

Revision ID: a1c4e7f2b9d3
Revises: 6d5db0f826f0
Create Date: 2026-11-20 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = 'a1c4e7f2b9d3'
down_revision: Union[str, Sequence[str], None] = '6d5db0f826f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATEMENTS = [
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_brands AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(p.id ORDER BY p.id))[1] AS canonical_id,
            ARRAY_AGG(DISTINCT p.id) AS production_ids,
            ARRAY_AGG(DISTINCT p.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object('id', r.id, 'name', r.name, 'lattes_id', r.lattes_id)) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            COALESCE(MAX(p.title), '') AS title,
            p.year,
            MAX(p.nature) AS nature,
            MAX(p.goal) AS goal
        FROM brand p
        LEFT JOIN researcher r ON r.id = p.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = p.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = p.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        GROUP BY LOWER(UNACCENT(TRIM(COALESCE(p.title, '')))), p.year
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        COALESCE(collection_slugs, '{}') AS collection_slugs,
        platform_authors,
        title,
        year,
        nature,
        goal,
        (setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A') || setweight(to_tsvector('pt_unaccent', coalesce(goal, '')), 'B')) AS search_vector
    FROM deduplicated;
    """,
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_brands_pk ON mv_canonical_brands (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_brands_year ON mv_canonical_brands (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_brands_researcher_ids ON mv_canonical_brands USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_brands_institution_ids ON mv_canonical_brands USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_brands_graduate_program_ids ON mv_canonical_brands USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_brands_collection_slugs ON mv_canonical_brands USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_brands_production_ids ON mv_canonical_brands USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_brands_search_vector ON mv_canonical_brands USING GIN (search_vector);',
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_guidance AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(p.id ORDER BY p.id))[1] AS canonical_id,
            ARRAY_AGG(DISTINCT p.id) AS production_ids,
            ARRAY_AGG(DISTINCT p.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object('id', r.id, 'name', r.name, 'lattes_id', r.lattes_id)) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            COALESCE(MAX(p.title), '') AS title,
            p.year,
            MAX(p.nature) AS nature,
            MAX(p.type) AS type,
            MAX(p.status) AS status,
            MAX(p.oriented) AS oriented
        FROM guidance p
        LEFT JOIN researcher r ON r.id = p.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = p.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = p.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        GROUP BY LOWER(UNACCENT(TRIM(COALESCE(p.title, '')))), LOWER(UNACCENT(TRIM(COALESCE(p.oriented, '')))), p.year
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        COALESCE(collection_slugs, '{}') AS collection_slugs,
        platform_authors,
        title,
        year,
        nature,
        type,
        status,
        oriented,
        (setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A') || setweight(to_tsvector('pt_unaccent', coalesce(oriented, '')), 'B')) AS search_vector
    FROM deduplicated;
    """,
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_guidance_pk ON mv_canonical_guidance (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_guidance_year ON mv_canonical_guidance (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_guidance_researcher_ids ON mv_canonical_guidance USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_guidance_institution_ids ON mv_canonical_guidance USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_guidance_graduate_program_ids ON mv_canonical_guidance USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_guidance_collection_slugs ON mv_canonical_guidance USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_guidance_production_ids ON mv_canonical_guidance USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_guidance_search_vector ON mv_canonical_guidance USING GIN (search_vector);',
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_reports AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(p.id ORDER BY p.id))[1] AS canonical_id,
            ARRAY_AGG(DISTINCT p.id) AS production_ids,
            ARRAY_AGG(DISTINCT p.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object('id', r.id, 'name', r.name, 'lattes_id', r.lattes_id)) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            COALESCE(MAX(p.title), '') AS title,
            p.year,
            MAX(p.project_name) AS project_name,
            MAX(p.financing_institutionc) AS financing
        FROM research_report p
        LEFT JOIN researcher r ON r.id = p.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = p.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = p.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        GROUP BY LOWER(UNACCENT(TRIM(COALESCE(p.title, '')))), p.year
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        COALESCE(collection_slugs, '{}') AS collection_slugs,
        platform_authors,
        title,
        year,
        project_name,
        financing,
        (setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A') || setweight(to_tsvector('pt_unaccent', coalesce(project_name, '')), 'B')) AS search_vector
    FROM deduplicated;
    """,
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_reports_pk ON mv_canonical_reports (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_reports_year ON mv_canonical_reports (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_reports_researcher_ids ON mv_canonical_reports USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_reports_institution_ids ON mv_canonical_reports USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_reports_graduate_program_ids ON mv_canonical_reports USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_reports_collection_slugs ON mv_canonical_reports USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_reports_production_ids ON mv_canonical_reports USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_reports_search_vector ON mv_canonical_reports USING GIN (search_vector);',
]


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_canonical_reports CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_canonical_guidance CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_canonical_brands CASCADE;')
