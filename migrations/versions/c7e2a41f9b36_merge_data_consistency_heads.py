"""Merge data consistency and upstream migration heads.

Revision ID: c7e2a41f9b36
Revises: 4a1b2c3d4e5f, 6d5db0f826f0, 9e12486e01a7
"""

from typing import Sequence, Union

revision: str = 'c7e2a41f9b36'
down_revision: Union[str, Sequence[str], None] = (
    '4a1b2c3d4e5f',
    '6d5db0f826f0',
    '9e12486e01a7',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
