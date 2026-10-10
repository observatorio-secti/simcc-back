"""create_mv_canonical_research_projects

Revision ID: 3c5e8a1f2b7d
Revises: 04f07a6152c0
Create Date: 2026-10-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3c5e8a1f2b7d'
down_revision: Union[str, Sequence[str], None] = '04f07a6152c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Um mesmo projeto aparece no Lattes de cada integrante: desduplica por
    # nome normalizado + ano de início. Fomentos, integrantes e produções
    # vinculadas vêm das tabelas filhas de todas as cópias do projeto.
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_research_projects AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(rp.id ORDER BY rp.id))[1] AS canonical_id,
            ARRAY_AGG(DISTINCT rp.id) AS production_ids,
            ARRAY_AGG(DISTINCT rp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            MAX(rp.project_name) AS title,
            rp.start_year,
            MAX(rp.end_year) AS end_year,
            MAX(rp.status) AS status,
            MAX(rp.nature) AS nature,
            MAX(rp.agency_name) AS agency_name,
            MAX(rp.agency_code) AS agency_code,
            MAX(rp.description) AS description,
            MAX(rp.number_undergraduates) AS number_undergraduates,
            MAX(rp.number_specialists) AS number_specialists,
            MAX(rp.number_academic_masters) AS number_academic_masters,
            MAX(rp.number_phd) AS number_phd
        FROM research_project rp
        LEFT JOIN researcher r ON r.id = rp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = rp.researcher_id
        WHERE NULLIF(TRIM(rp.project_name), '') IS NOT NULL
        GROUP BY
            LOWER(UNACCENT(TRIM(rp.project_name))),
            rp.start_year
    )
    SELECT
        d.canonical_id,
        d.production_ids,
        d.researcher_ids,
        d.institution_ids,
        d.graduate_program_ids,
        d.platform_authors,
        d.title,
        d.start_year AS year,
        d.start_year,
        d.end_year,
        d.status,
        d.nature,
        d.agency_name,
        d.agency_code,
        d.description,
        d.number_undergraduates,
        d.number_specialists,
        d.number_academic_masters,
        d.number_phd,
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'agency_name', f.agency_name,
                'agency_code', f.agency_code,
                'nature', f.nature
            ))
            FROM research_project_foment f
            WHERE f.project_id = ANY(d.production_ids)
        ) AS foment,
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'name', c.name,
                'lattes_id', c.lattes_id,
                'citations', c.citations,
                'coordinator', c.coordinator
            ))
            FROM research_project_components c
            WHERE c.project_id = ANY(d.production_ids)
        ) AS components,
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'title', p.title,
                'type', p.type
            ))
            FROM research_project_production p
            WHERE p.project_id = ANY(d.production_ids)
        ) AS productions,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(d.title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(d.description, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(d.agency_name, '') || ' ' || coalesce(d.nature, '')), 'C')
        ) AS search_vector
    FROM deduplicated d;
    """)

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_projects_pk ON mv_canonical_research_projects (canonical_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_year ON mv_canonical_research_projects (year DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_researchers ON mv_canonical_research_projects USING GIN (researcher_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_institutions ON mv_canonical_research_projects USING GIN (institution_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_programs ON mv_canonical_research_projects USING GIN (graduate_program_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_prods ON mv_canonical_research_projects USING GIN (production_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_projects_vector ON mv_canonical_research_projects USING GIN (search_vector);")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_canonical_research_projects CASCADE;")
