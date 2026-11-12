"""add_indexes_to_education_address_foment

Revision ID: 0edbb54703e7
Revises: 8467ac465ad9
Create Date: 2026-11-12 15:59:52.769118

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0edbb54703e7'
down_revision: Union[str, Sequence[str], None] = '8467ac465ad9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'idx_education_researcher_id',
        'education',
        ['researcher_id'],
        unique=False,
    )
    op.create_index(
        'idx_researcher_address_researcher_id',
        'researcher_address',
        ['researcher_id'],
        unique=True,
    )
    op.create_index(
        'idx_foment_researcher_id',
        'foment',
        ['researcher_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'idx_foment_researcher_id',
        table_name='foment',
    )
    op.drop_index(
        'idx_researcher_address_researcher_id',
        table_name='researcher_address',
    )
    op.drop_index(
        'idx_education_researcher_id',
        table_name='education',
    )
