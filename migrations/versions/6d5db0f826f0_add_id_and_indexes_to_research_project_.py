"""add_id_and_indexes_to_research_project_foment_components

Revision ID: 6d5db0f826f0
Revises: 0edbb54703e7
Create Date: 2026-11-12 23:13:40.274841

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6d5db0f826f0'
down_revision: Union[str, Sequence[str], None] = '0edbb54703e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add index on research_project_components(project_id)
    and migrate research_project_foment to have its own UUID primary key
    and index on project_id.
    """
    op.create_index(
        'idx_research_project_components_project_id',
        'research_project_components',
        ['project_id'],
        unique=False,
    )

    op.drop_constraint(
        'research_project_foment_pkey',
        'research_project_foment',
        type_='primary',
    )
    op.add_column(
        'research_project_foment',
        sa.Column(
            'id',
            sa.UUID(),
            server_default=sa.text('gen_random_uuid()'),
            nullable=False,
        ),
    )
    op.create_primary_key(
        'research_project_foment_pkey',
        'research_project_foment',
        ['id'],
    )
    op.create_index(
        'idx_research_project_foment_project_id',
        'research_project_foment',
        ['project_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'idx_research_project_foment_project_id',
        table_name='research_project_foment',
    )
    op.drop_constraint(
        'research_project_foment_pkey',
        'research_project_foment',
        type_='primary',
    )
    op.drop_column('research_project_foment', 'id')
    op.create_primary_key(
        'research_project_foment_pkey',
        'research_project_foment',
        ['project_id'],
    )

    op.drop_index(
        'idx_research_project_components_project_id',
        table_name='research_project_components',
    )
