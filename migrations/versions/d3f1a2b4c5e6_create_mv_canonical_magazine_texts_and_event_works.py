# ruff: noqa: E501, W291, W293
"""create mv_canonical_magazine_texts and mv_canonical_event_works

Revision ID: d3f1a2b4c5e6
Revises: c2e4f6a8b0d1
Create Date: 2026-11-22 06:25:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = 'd3f1a2b4c5e6'
down_revision: Union[str, Sequence[str], None] = 'c2e4f6a8b0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATEMENTS = [
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_magazine_texts AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(bp.id ORDER BY bp.id))[1] AS canonical_id,
            ARRAY_AGG(DISTINCT bp.id) AS production_ids,
            ARRAY_AGG(DISTINCT bp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object('id', r.id, 'name', r.name, 'lattes_id', r.lattes_id)) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            COALESCE(MAX(bp.title), '') AS title,
            MAX(bp.title_en) AS title_en,
            bp.year_ AS year,
            MAX(bp.nature) AS nature,
            MAX(bp.language) AS language,
            MAX(bp.means_divulgation) AS means_divulgation,
            MAX(bp.homepage) AS homepage,
            BOOL_OR(bp.relevance) AS relevance,
            BOOL_OR(bp.scientific_divulgation) AS scientific_divulgation,
            MAX(bp.authors) AS all_authors_raw
        FROM bibliographic_production bp
        LEFT JOIN researcher r ON r.id = bp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = bp.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = bp.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        WHERE bp.type = 'TEXT_IN_NEWSPAPER_MAGAZINE'
        GROUP BY LOWER(UNACCENT(TRIM(COALESCE(bp.title, '')))), bp.year_
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
        title_en,
        year,
        nature,
        language,
        means_divulgation,
        homepage,
        relevance,
        scientific_divulgation,
        all_authors_raw,
        (setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A') || setweight(to_tsvector('pt_unaccent', coalesce(title_en, '')), 'B')) AS search_vector
    FROM deduplicated;
    """,
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_magazine_texts_pk ON mv_canonical_magazine_texts (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_magazine_texts_year ON mv_canonical_magazine_texts (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_magazine_texts_researcher_ids ON mv_canonical_magazine_texts USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_magazine_texts_institution_ids ON mv_canonical_magazine_texts USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_magazine_texts_graduate_program_ids ON mv_canonical_magazine_texts USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_magazine_texts_collection_slugs ON mv_canonical_magazine_texts USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_magazine_texts_production_ids ON mv_canonical_magazine_texts USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_magazine_texts_search_vector ON mv_canonical_magazine_texts USING GIN (search_vector);',
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_event_works AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(bp.id ORDER BY bp.id))[1] AS canonical_id,
            ARRAY_AGG(DISTINCT bp.id) AS production_ids,
            ARRAY_AGG(DISTINCT bp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            ARRAY_AGG(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs,
            jsonb_agg(DISTINCT jsonb_build_object('id', r.id, 'name', r.name, 'lattes_id', r.lattes_id)) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            COALESCE(MAX(bp.title), '') AS title,
            MAX(bp.title_en) AS title_en,
            bp.year_ AS year,
            MAX(bp.nature) AS nature,
            MAX(bp.language) AS language,
            MAX(bp.means_divulgation) AS means_divulgation,
            MAX(bp.homepage) AS homepage,
            BOOL_OR(bp.relevance) AS relevance,
            BOOL_OR(bp.scientific_divulgation) AS scientific_divulgation,
            MAX(bp.authors) AS all_authors_raw,
            MAX(bpew.event_name) AS event_name,
            MAX(bpew.event_classification) AS event_classification,
            MAX(bpew.event_city) AS event_city,
            MAX(bpew.event_year) AS event_year,
            MAX(bpew.proceedings_title) AS proceedings_title,
            MAX(bpew.volume) AS volume,
            MAX(bpew.issue) AS issue,
            MAX(bpew.series) AS series,
            MAX(bpew.start_page) AS start_page,
            MAX(bpew.end_page) AS end_page,
            MAX(bpew.publisher_name) AS publisher_name,
            MAX(bpew.publisher_city) AS publisher_city,
            MAX(bpew.isbn) AS isbn
        FROM bibliographic_production bp
        LEFT JOIN bibliographic_production_work_in_event bpew ON bpew.bibliographic_production_id = bp.id
        LEFT JOIN researcher r ON r.id = bp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = bp.researcher_id
        LEFT JOIN researcher_collection rc ON rc.researcher_id = bp.researcher_id
        LEFT JOIN collection c ON c.id = rc.collection_id
        WHERE bp.type = 'WORK_IN_EVENT'
        GROUP BY LOWER(UNACCENT(TRIM(COALESCE(bp.title, '')))), bp.year_
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
        title_en,
        year,
        nature,
        language,
        means_divulgation,
        homepage,
        relevance,
        scientific_divulgation,
        all_authors_raw,
        event_name,
        event_classification,
        event_city,
        event_year,
        proceedings_title,
        volume,
        issue,
        series,
        start_page,
        end_page,
        publisher_name,
        publisher_city,
        isbn,
        (setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A') || setweight(to_tsvector('pt_unaccent', coalesce(event_name, '')), 'B')) AS search_vector
    FROM deduplicated;
    """,
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_event_works_pk ON mv_canonical_event_works (canonical_id);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_event_works_year ON mv_canonical_event_works (year DESC);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_event_works_researcher_ids ON mv_canonical_event_works USING GIN (researcher_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_event_works_institution_ids ON mv_canonical_event_works USING GIN (institution_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_event_works_graduate_program_ids ON mv_canonical_event_works USING GIN (graduate_program_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_event_works_collection_slugs ON mv_canonical_event_works USING GIN (collection_slugs);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_event_works_production_ids ON mv_canonical_event_works USING GIN (production_ids);',
    'CREATE INDEX IF NOT EXISTS idx_mv_canonical_event_works_search_vector ON mv_canonical_event_works USING GIN (search_vector);',
]


def upgrade() -> None:
    for stmt in STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_canonical_event_works CASCADE;')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS mv_canonical_magazine_texts CASCADE;')
