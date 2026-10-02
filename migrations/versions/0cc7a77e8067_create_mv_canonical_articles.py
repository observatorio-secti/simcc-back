"""create_mv_canonical_articles

Revision ID: 0cc7a77e8067
Revises: 8ae74128eb49
Create Date: 2026-10-02 10:12:57.241439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cc7a77e8067'
down_revision: Union[str, Sequence[str], None] = '8ae74128eb49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_canonical_articles AS
    WITH deduplicated AS (
        SELECT
            (ARRAY_AGG(bp.id))[1] AS canonical_id,
            ARRAY_AGG(bp.id) AS production_ids,
            ARRAY_AGG(DISTINCT bp.researcher_id) AS researcher_ids,
            ARRAY_AGG(DISTINCT r.institution_id) FILTER (WHERE r.institution_id IS NOT NULL) AS institution_ids,
            ARRAY_AGG(DISTINCT gpr.graduate_program_id) FILTER (WHERE gpr.graduate_program_id IS NOT NULL) AS graduate_program_ids,
            jsonb_agg(DISTINCT jsonb_build_object(
                'id', r.id,
                'name', r.name,
                'lattes_id', r.lattes_id
            )) FILTER (WHERE r.id IS NOT NULL) AS platform_authors,
            bp.title,
            bp.year_,
            bp.doi,
            MAX(bpa.qualis) AS qualis,
            MAX(bpa.jcr) AS jcr,
            MAX(bpa.periodical_magazine_name) AS magazine_name,
            MAX(bpa.issn) AS issn,
            MAX(oa.abstract) AS abstract,
            COALESCE(MAX(oa.citations_count), 0) AS citations_count,
            MAX(oa.landing_page_url) AS landing_page_url,
            MAX(oa.pdf) AS pdf_url,
            MAX(oa.keywords) AS keywords,
            MAX(bp.authors) AS all_authors_raw,
            MAX(oa.language) AS language
        FROM bibliographic_production bp
        JOIN bibliographic_production_article bpa ON bpa.bibliographic_production_id = bp.id
        LEFT JOIN researcher r ON r.id = bp.researcher_id
        LEFT JOIN graduate_program_researcher gpr ON gpr.researcher_id = bp.researcher_id
        LEFT JOIN openalex_article oa ON oa.article_id = bp.id
        WHERE bp.type = 'ARTICLE'
        GROUP BY 
            COALESCE(NULLIF(LOWER(TRIM(bp.doi)), ''), LOWER(UNACCENT(TRIM(bp.title)))),
            bp.title,
            bp.year_,
            bp.doi
    )
    SELECT
        canonical_id,
        production_ids,
        researcher_ids,
        institution_ids,
        graduate_program_ids,
        platform_authors,
        title,
        year_ AS year,
        doi,
        qualis,
        jcr,
        magazine_name,
        issn,
        abstract,
        citations_count,
        landing_page_url,
        pdf_url,
        keywords,
        all_authors_raw,
        language,
        (abstract IS NOT NULL AND length(abstract) > 0) AS has_abstract,
        (pdf_url IS NOT NULL AND length(pdf_url) > 0) AS has_open_access_pdf,
        (
            setweight(to_tsvector('pt_unaccent', coalesce(title, '')), 'A')
            || setweight(to_tsvector('pt_unaccent', coalesce(keywords, '')), 'B')
            || setweight(to_tsvector('pt_unaccent', coalesce(abstract, '')), 'C')
            || setweight(to_tsvector('pt_unaccent', coalesce(magazine_name, '') || ' ' || coalesce(issn, '')), 'D')
        ) AS search_vector
    FROM deduplicated;
    """)

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_canonical_articles_pk ON mv_canonical_articles (canonical_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_doi ON mv_canonical_articles (doi);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_year ON mv_canonical_articles (year DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_citations ON mv_canonical_articles (citations_count DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_qualis ON mv_canonical_articles (qualis);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_researchers ON mv_canonical_articles USING GIN (researcher_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_institutions ON mv_canonical_articles USING GIN (institution_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_programs ON mv_canonical_articles USING GIN (graduate_program_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_prods ON mv_canonical_articles USING GIN (production_ids);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mv_canonical_articles_vector ON mv_canonical_articles USING GIN (search_vector);")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_canonical_articles CASCADE;")
