"""create data consistency load and snapshot tables

Revision ID: 4a1b2c3d4e5f
Revises: 3c5e8a1f2b7d
Create Date: 2026-11-01 02:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '4a1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '3c5e8a1f2b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'data_load_run',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            server_default=sa.text('gen_random_uuid()'),
            nullable=False,
        ),
        sa.Column('load_type', sa.String(length=80), nullable=False),
        sa.Column(
            'status',
            sa.String(length=30),
            server_default=sa.text("'RUNNING'"),
            nullable=False,
        ),
        sa.Column('trigger_source', sa.String(length=30), nullable=False),
        sa.Column(
            'started_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_data_load_run_type_started',
        'data_load_run',
        ['load_type', 'started_at'],
    )
    op.create_index(
        'idx_data_load_run_status', 'data_load_run', ['status']
    )

    op.create_table(
        'data_snapshot_metric',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            server_default=sa.text('gen_random_uuid()'),
            nullable=False,
        ),
        sa.Column(
            'load_run_id', postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column('phase', sa.String(length=10), nullable=False),
        sa.Column('metric_key', sa.String(length=100), nullable=False),
        sa.Column('scope', sa.String(length=20), nullable=False),
        sa.Column(
            'institution_id', postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column('institution_name', sa.String(), nullable=True),
        sa.Column('value_numeric', sa.BigInteger(), nullable=False),
        sa.Column(
            'captured_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['institution_id'],
            ['institution.id'],
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['load_run_id'],
            ['data_load_run.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'load_run_id',
            'phase',
            'metric_key',
            'scope',
            'institution_id',
            name='uq_data_snapshot_metric_identity',
        ),
    )
    op.create_index(
        'idx_data_snapshot_metric_run_phase',
        'data_snapshot_metric',
        ['load_run_id', 'phase'],
    )
    op.create_index(
        'idx_data_snapshot_metric_lookup',
        'data_snapshot_metric',
        ['metric_key', 'scope', 'institution_id'],
    )

    op.create_table(
        'data_consistency_result',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            server_default=sa.text('gen_random_uuid()'),
            nullable=False,
        ),
        sa.Column(
            'load_run_id', postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column('metric_key', sa.String(length=100), nullable=False),
        sa.Column('scope', sa.String(length=20), nullable=False),
        sa.Column(
            'institution_id', postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column('institution_name', sa.String(), nullable=True),
        sa.Column('before_value', sa.BigInteger(), nullable=False),
        sa.Column('after_value', sa.BigInteger(), nullable=False),
        sa.Column('absolute_difference', sa.BigInteger(), nullable=False),
        sa.Column('variation_percent', sa.Numeric(12, 4), nullable=True),
        sa.Column(
            'lower_threshold',
            sa.Numeric(6, 3),
            server_default=sa.text('5'),
            nullable=False,
        ),
        sa.Column(
            'upper_threshold',
            sa.Numeric(6, 3),
            server_default=sa.text('10'),
            nullable=False,
        ),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column(
            'is_warning',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
        ),
        sa.Column('warning_reason', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['institution_id'],
            ['institution.id'],
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['load_run_id'],
            ['data_load_run.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'load_run_id',
            'metric_key',
            'scope',
            'institution_id',
            name='uq_data_consistency_result_identity',
        ),
    )
    op.create_index(
        'idx_data_consistency_result_run_warning',
        'data_consistency_result',
        ['load_run_id', 'is_warning'],
    )
    op.create_index(
        'idx_data_consistency_result_metric_scope',
        'data_consistency_result',
        ['metric_key', 'scope', 'institution_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'idx_data_consistency_result_metric_scope',
        table_name='data_consistency_result',
    )
    op.drop_index(
        'idx_data_consistency_result_run_warning',
        table_name='data_consistency_result',
    )
    op.drop_table('data_consistency_result')
    op.drop_index(
        'idx_data_snapshot_metric_lookup',
        table_name='data_snapshot_metric',
    )
    op.drop_index(
        'idx_data_snapshot_metric_run_phase',
        table_name='data_snapshot_metric',
    )
    op.drop_table('data_snapshot_metric')
    op.drop_index(
        'idx_data_load_run_status',
        table_name='data_load_run',
    )
    op.drop_index(
        'idx_data_load_run_type_started',
        table_name='data_load_run',
    )
    op.drop_table('data_load_run')
