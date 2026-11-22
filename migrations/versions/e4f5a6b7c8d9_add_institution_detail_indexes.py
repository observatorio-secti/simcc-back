"""add institution detail indexes

Revision ID: e4f5a6b7c8d9
Revises: d3f1a2b4c5e6
Create Date: 2026-11-22 17:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3f1a2b4c5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create indexes for institution detail counts and breakdowns."""
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_researcher_institution_inst_res '
        'ON researcher_institution (institution_id, researcher_id);'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_research_group_first_leader '
        'ON research_group (first_leader_id) '
        'WHERE first_leader_id IS NOT NULL;'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_research_group_second_leader '
        'ON research_group (second_leader_id) '
        'WHERE second_leader_id IS NOT NULL;'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_labs_institution_id '
        'ON labs (institution_id) '
        'WHERE institution_id IS NOT NULL;'
    )


def downgrade() -> None:
    """Drop institution detail indexes."""
    op.execute('DROP INDEX IF EXISTS idx_labs_institution_id;')
    op.execute('DROP INDEX IF EXISTS idx_research_group_second_leader;')
    op.execute('DROP INDEX IF EXISTS idx_research_group_first_leader;')
    op.execute('DROP INDEX IF EXISTS idx_researcher_institution_inst_res;')
