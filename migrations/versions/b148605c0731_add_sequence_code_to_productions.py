"""add_sequence_code_to_productions

Revision ID: b148605c0731
Revises: b7d2c4e9a1f3
Create Date: 2026-10-08 22:56:13.867158

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b148605c0731'
down_revision: Union[str, Sequence[str], None] = 'b7d2c4e9a1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRODUCTION_TABLES = [
    'advisory_activity',
    'artistic_production',
    'bibliographic_production',
    'brand',
    'didactic_material',
    'event_organization',
    'foment',
    'guidance',
    'industrial_design',
    'letter_map_or_similar',
    'maintenance_artistic_work',
    'mockup',
    'other_technical_production',
    'participation_events',
    'patent',
    'process_or_technique',
    'publishing',
    'radio_or_tv_program',
    'registered_cultivar',
    'research_project',
    'research_report',
    'short_course',
    'short_course_taught',
    'social_media_website_blog',
    'software',
    'technical_work',
    'technical_work_presentation',
    'technical_work_program',
    'technological_product',
]


def upgrade() -> None:
    for table_name in PRODUCTION_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                'sequence_code',
                sa.Integer(),
                nullable=False,
                server_default=sa.text('0'),
            ),
        )
        op.alter_column(table_name, 'sequence_code', server_default=None)


def downgrade() -> None:
    for table_name in reversed(PRODUCTION_TABLES):
        op.drop_column(table_name, 'sequence_code')
