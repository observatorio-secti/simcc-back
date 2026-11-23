"""make labs researcher_id nullable

Revision ID: f1a2b3c4d5e6
Revises: e4f5a6b7c8d9
Create Date: 2026-11-23 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow labs without researcher_id (associated via institution_id)."""
    op.alter_column(
        'labs',
        'researcher_id',
        existing_type=sa.UUID(),
        nullable=True,
    )
    op.drop_constraint(
        op.f('labs_researcher_id_fkey'), 'labs', type_='foreignkey'
    )
    op.create_foreign_key(
        op.f('labs_researcher_id_fkey'),
        'labs',
        'researcher',
        ['researcher_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Restore NOT NULL and CASCADE on labs.researcher_id."""
    op.drop_constraint(
        op.f('labs_researcher_id_fkey'), 'labs', type_='foreignkey'
    )
    op.create_foreign_key(
        op.f('labs_researcher_id_fkey'),
        'labs',
        'researcher',
        ['researcher_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.alter_column(
        'labs',
        'researcher_id',
        existing_type=sa.UUID(),
        nullable=False,
    )
