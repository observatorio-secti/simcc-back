"""Serviço para atualização e rastreamento das MVs de busca."""

import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

SEARCH_MATERIALIZED_VIEWS = [
    'mv_search_articles',
    'mv_search_books',
    'mv_search_patents',
    'mv_search_software',
    'mv_search_documents',
    'mv_researcher_search',
]


class MVRefreshState:
    """Estado em memória do rastreamento de atualização das MVs."""

    last_refresh_timestamp: Optional[datetime] = None


async def refresh_search_materialized_views(
    session: AsyncSession,
    concurrently: bool = False,
) -> None:
    """Atualiza todas as MVs de busca na ordem de dependência correta.

    Quando `concurrently=True`, executa com CONCURRENTLY (não pode rodar
    dentro de bloco de transação). Quando `False`, executa REFRESH padrão.
    """
    concurrent_sql = 'CONCURRENTLY' if concurrently else ''

    for view_name in SEARCH_MATERIALIZED_VIEWS:
        t0 = time.perf_counter()
        await session.execute(
            text(f'REFRESH MATERIALIZED VIEW {concurrent_sql} {view_name};')
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)

        # Atualiza o timestamp de refresh na tabela de metadados
        await session.execute(
            text(
                """
                INSERT INTO mv_refresh_metadata
                    (view_name, refreshed_at, duration_ms)
                VALUES
                    (:view_name, now(), :duration_ms)
                ON CONFLICT (view_name) DO UPDATE
                SET refreshed_at = EXCLUDED.refreshed_at,
                    duration_ms = EXCLUDED.duration_ms;
                """
            ),
            {'view_name': view_name, 'duration_ms': duration_ms},
        )

    MVRefreshState.last_refresh_timestamp = datetime.now(timezone.utc)


def set_last_refresh_timestamp(timestamp: Optional[datetime]) -> None:
    """Define o timestamp em memória do último refresh das MVs."""
    MVRefreshState.last_refresh_timestamp = timestamp


def get_last_refresh_timestamp() -> Optional[datetime]:
    """Retorna o timestamp em memória do último refresh das MVs."""
    return MVRefreshState.last_refresh_timestamp
