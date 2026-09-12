"""Add researcher institution territory and weekly workload.

Revision ID: 42b8e719dc60
Revises: 9e12486e01a7
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '42b8e719dc60'
down_revision = '9e12486e01a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'researcher_institution',
        sa.Column(
            'researcher_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('researcher.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        sa.Column(
            'institution_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('institution.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        sa.Column('territorio_identidade', sa.String(), nullable=True),
        sa.Column('carga_horaria', sa.Numeric(5, 2), nullable=True),
        sa.CheckConstraint(
            'carga_horaria >= 0 AND carga_horaria <= 168',
            name='ck_researcher_institution_carga_horaria',
        ),
    )
    op.execute("""
        INSERT INTO researcher_institution (researcher_id, institution_id)
        SELECT id, institution_id FROM researcher
        WHERE institution_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_table('researcher_institution')
