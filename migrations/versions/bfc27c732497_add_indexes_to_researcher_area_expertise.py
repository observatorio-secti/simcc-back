"""add_indexes_to_researcher_area_expertise

Revision ID: bfc27c732497
Revises: 4d8e9f2a1b3c
Create Date: 2026-10-31 19:55:05.864059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bfc27c732497'
down_revision: Union[str, Sequence[str], None] = '4d8e9f2a1b3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'idx_researcher_area_expertise_researcher_order',
        'researcher_area_expertise',
        ['researcher_id', 'order'],
        unique=False,
    )
    op.create_index(
        'idx_researcher_area_expertise_researcher_id',
        'researcher_area_expertise',
        ['researcher_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'idx_researcher_area_expertise_researcher_id',
        table_name='researcher_area_expertise',
    )
    op.drop_index(
        'idx_researcher_area_expertise_researcher_order',
        table_name='researcher_area_expertise',
    )
