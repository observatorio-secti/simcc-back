"""Merge geo reference and data consistency migration heads.

A migração geográfica (a7c3e9f1b2d4, depois de labs f1a2b3c4d5e6) e a do
módulo de consistência (c7e2a41f9b36, PR #24) partiram de linhas
diferentes. Sem este merge, `alembic upgrade head` falha com duas heads.

Revision ID: d9b4f2c6a8e1
Revises: a7c3e9f1b2d4, c7e2a41f9b36
Create Date: 2026-11-23 21:00:00.000000

"""

from typing import Sequence, Union

revision: str = 'd9b4f2c6a8e1'
down_revision: Union[str, Sequence[str], None] = (
    'a7c3e9f1b2d4',
    'c7e2a41f9b36',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
