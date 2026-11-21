"""add ondelete cascade to production and project children

Revision ID: c2e4f6a8b0d1
Revises: a1c4e7f2b9d3
Create Date: 2026-11-21 13:07:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = 'c2e4f6a8b0d1'
down_revision: Union[str, Sequence[str], None] = 'a1c4e7f2b9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FKS: tuple[tuple[str, str, str, str], ...] = (
    (
        'bibliographic_production_artic_bibliographic_production_id_fkey',
        'bibliographic_production_article',
        'bibliographic_production_id',
        'bibliographic_production',
    ),
    (
        'bibliographic_production_book_bibliographic_production_id_fkey',
        'bibliographic_production_book',
        'bibliographic_production_id',
        'bibliographic_production',
    ),
    (
        'bibliographic_production_book__bibliographic_production_id_fkey',
        'bibliographic_production_book_chapter',
        'bibliographic_production_id',
        'bibliographic_production',
    ),
    (
        'bibliographic_production_work__bibliographic_production_id_fkey',
        'bibliographic_production_work_in_event',
        'bibliographic_production_id',
        'bibliographic_production',
    ),
    (
        'process_author_process_id_fkey',
        'process_author',
        'process_id',
        'process_or_technique',
    ),
    (
        'process_keyword_process_id_fkey',
        'process_keyword',
        'process_id',
        'process_or_technique',
    ),
    (
        'process_knowledge_area_process_id_fkey',
        'process_knowledge_area',
        'process_id',
        'process_or_technique',
    ),
    (
        'research_project_components_project_id_fkey',
        'research_project_components',
        'project_id',
        'research_project',
    ),
    (
        'research_project_foment_project_id_fkey',
        'research_project_foment',
        'project_id',
        'research_project',
    ),
    (
        'research_project_production_project_id_fkey',
        'research_project_production',
        'project_id',
        'research_project',
    ),
)


def upgrade() -> None:
    for fk_name, table, col, ref_table in _FKS:
        op.drop_constraint(fk_name, table, type_='foreignkey')
        op.create_foreign_key(
            fk_name,
            table,
            ref_table,
            [col],
            ['id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    for fk_name, table, col, ref_table in _FKS:
        op.drop_constraint(fk_name, table, type_='foreignkey')
        op.create_foreign_key(
            fk_name,
            table,
            ref_table,
            [col],
            ['id'],
        )
