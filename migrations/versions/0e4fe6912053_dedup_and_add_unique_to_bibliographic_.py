"""dedup_and_add_unique_to_bibliographic_production_children

Revision ID: 0e4fe6912053
Revises: 8d41c7b0e2a5
Create Date: 2026-09-30 23:37:09.422979

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0e4fe6912053'
down_revision: Union[str, Sequence[str], None] = '8d41c7b0e2a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: remove duplicates keeping most complete record,

    then add unique constraints.
    """
    # 1. Deduplicação em bibliographic_production_article
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY bibliographic_production_id
                       ORDER BY (
                           (CASE WHEN volume IS NOT NULL AND volume != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN fascicle IS NOT NULL AND fascicle != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN series IS NOT NULL AND series != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN start_page IS NOT NULL
                            AND start_page != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN end_page IS NOT NULL AND end_page != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN place_publication IS NOT NULL
                            AND place_publication != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN periodical_magazine_name IS NOT NULL
                            AND periodical_magazine_name != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN issn IS NOT NULL AND issn != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN qualis IS NOT NULL AND qualis != ''
                            AND qualis != 'SQ'
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN jcr IS NOT NULL AND jcr != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN jcr_link IS NOT NULL AND jcr_link != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN stars IS NOT NULL AND stars > 0
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN quadrennial IS NOT NULL
                            AND quadrennial != ''
                            THEN 1 ELSE 0 END)
                       ) DESC,
                       id DESC
                   ) AS rn
            FROM bibliographic_production_article
        )
        DELETE FROM bibliographic_production_article
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
        """
    )

    # 2. Deduplicação em bibliographic_production_book
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY bibliographic_production_id
                       ORDER BY (
                           (CASE WHEN isbn IS NOT NULL AND isbn != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN qtt_volume IS NOT NULL
                            AND qtt_volume != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN qtt_pages IS NOT NULL
                            AND qtt_pages != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN num_edition_revision IS NOT NULL
                            AND num_edition_revision != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN num_series IS NOT NULL
                            AND num_series != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN publishing_company IS NOT NULL
                            AND publishing_company != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN publishing_company_city IS NOT NULL
                            AND publishing_company_city != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN stars IS NOT NULL AND stars > 0
                            THEN 1 ELSE 0 END)
                       ) DESC,
                       id DESC
                   ) AS rn
            FROM bibliographic_production_book
        )
        DELETE FROM bibliographic_production_book
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
        """
    )

    # 3. Deduplicação em bibliographic_production_book_chapter
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY bibliographic_production_id
                       ORDER BY (
                           (CASE WHEN book_title IS NOT NULL
                            AND book_title != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN isbn IS NOT NULL AND isbn != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN start_page IS NOT NULL
                            AND start_page != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN end_page IS NOT NULL AND end_page != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN qtt_volume IS NOT NULL
                            AND qtt_volume != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN organizers IS NOT NULL
                            AND organizers != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN num_edition_revision IS NOT NULL
                            AND num_edition_revision != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN num_series IS NOT NULL
                            AND num_series != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN publishing_company IS NOT NULL
                            AND publishing_company != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN publishing_company_city IS NOT NULL
                            AND publishing_company_city != ''
                            THEN 1 ELSE 0 END) +
                           (CASE WHEN stars IS NOT NULL AND stars > 0
                            THEN 1 ELSE 0 END)
                       ) DESC,
                       id DESC
                   ) AS rn
            FROM bibliographic_production_book_chapter
        )
        DELETE FROM bibliographic_production_book_chapter
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
        """
    )

    # 4. Criar Unique Constraints
    op.create_unique_constraint(
        'uq_bibliographic_production_article_bp_id',
        'bibliographic_production_article',
        ['bibliographic_production_id'],
    )
    op.create_unique_constraint(
        'uq_bibliographic_production_book_bp_id',
        'bibliographic_production_book',
        ['bibliographic_production_id'],
    )
    op.create_unique_constraint(
        'uq_bibliographic_production_book_chapter_bp_id',
        'bibliographic_production_book_chapter',
        ['bibliographic_production_id'],
    )


def downgrade() -> None:
    """Downgrade schema: drop unique constraints."""
    op.drop_constraint(
        'uq_bibliographic_production_book_chapter_bp_id',
        'bibliographic_production_book_chapter',
        type_='unique',
    )
    op.drop_constraint(
        'uq_bibliographic_production_book_bp_id',
        'bibliographic_production_book',
        type_='unique',
    )
    op.drop_constraint(
        'uq_bibliographic_production_article_bp_id',
        'bibliographic_production_article',
        type_='unique',
    )
