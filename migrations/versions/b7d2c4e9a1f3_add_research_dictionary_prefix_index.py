"""add_research_dictionary_prefix_index

Revision ID: b7d2c4e9a1f3
Revises: 6f10a3da5dce
Create Date: 2026-10-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b7d2c4e9a1f3'
down_revision: Union[str, Sequence[str], None] = '6f10a3da5dce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Busca por prefixo do GET /v2/suggestion (o índice trigram existente
    # não atende prefixos curtos nem devolve em ordem)
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_research_dictionary_term_prefix '
        'ON research_dictionary '
        '(public.f_unaccent(lower(term)) text_pattern_ops);'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP INDEX IF EXISTS idx_research_dictionary_term_prefix;')
