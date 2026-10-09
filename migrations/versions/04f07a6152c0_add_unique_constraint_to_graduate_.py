"""add_unique_constraint_to_graduate_program_researcher

Revision ID: 04f07a6152c0
Revises: b148605c0731
Create Date: 2026-10-09 19:33:11.310466

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '04f07a6152c0'
down_revision: Union[str, Sequence[str], None] = 'b148605c0731'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        'uq_graduate_program_researcher_program_researcher_year',
        'graduate_program_researcher',
        ['graduate_program_id', 'researcher_id', 'year'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'uq_graduate_program_researcher_program_researcher_year',
        'graduate_program_researcher',
        type_='unique',
    )
