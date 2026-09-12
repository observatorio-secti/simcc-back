"""normalize_researcher_institution_and_drop_custom_attributes

Revision ID: 9b38fbff8df4
Revises: 42b8e719dc60
Create Date: 2026-09-12 20:42:14.338213

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9b38fbff8df4'
down_revision: Union[str, Sequence[str], None] = '42b8e719dc60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Renomeia colunas para ingles e adiciona city_id
    # em researcher_institution
    op.alter_column(
        'researcher_institution',
        'territorio_identidade',
        new_column_name='identity_territory',
    )
    op.alter_column(
        'researcher_institution',
        'carga_horaria',
        new_column_name='workload',
    )
    op.drop_constraint(
        'ck_researcher_institution_carga_horaria',
        'researcher_institution',
        type_='check',
    )
    op.create_check_constraint(
        'ck_researcher_institution_workload',
        'researcher_institution',
        'workload >= 0 AND workload <= 168',
    )
    op.add_column(
        'researcher_institution',
        sa.Column(
            'city_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('city.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )

    # 2. Remove tabela legada researcher_custom_attributes
    op.execute('DROP TABLE IF EXISTS researcher_custom_attributes CASCADE;')


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Recria tabela researcher_custom_attributes
    op.create_table(
        'researcher_custom_attributes',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'researcher_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('researcher.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('gender', sa.String(), nullable=True),
        sa.Column('zip_code', sa.String(), nullable=True),
        sa.Column('work_regime', sa.String(), nullable=True),
        sa.Column(
            'custom_attributes',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # 2. Reverte researcher_institution
    op.drop_column('researcher_institution', 'city_id')
    op.drop_constraint(
        'ck_researcher_institution_workload',
        'researcher_institution',
        type_='check',
    )
    op.create_check_constraint(
        'ck_researcher_institution_carga_horaria',
        'researcher_institution',
        'carga_horaria >= 0 AND carga_horaria <= 168',
    )
    op.alter_column(
        'researcher_institution',
        'workload',
        new_column_name='carga_horaria',
    )
    op.alter_column(
        'researcher_institution',
        'identity_territory',
        new_column_name='territorio_identidade',
    )
