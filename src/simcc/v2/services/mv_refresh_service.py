"""Serviço para atualização e rastreamento das MVs de busca."""

import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

SEARCH_MATERIALIZED_VIEWS = [
    'mv_search_articles',
    'mv_search_books',
    'mv_search_patents',
    'mv_search_software',
    'mv_search_events',
    'mv_search_areas',
    'mv_search_documents',
    'mv_researcher_search',
    'mv_canonical_articles',
    'mv_canonical_books',
    'mv_canonical_book_chapters',
    'mv_canonical_software',
    'mv_canonical_patents',
    'mv_canonical_events',
    'mv_canonical_research_projects',
]


# Cache por processo do último refresh lido de `mv_refresh_metadata`.
# A API roda com vários workers e o refresh é feito pelo ETL, então a fonte
# de verdade é a tabela; a memória só evita uma consulta por requisição.
DATA_AS_OF_TTL_SECONDS = 60.0


class _DataAsOfCache:
    value: Optional[datetime] = None
    expires_at: float = 0.0


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

    _DataAsOfCache.value = datetime.now(timezone.utc)
    _DataAsOfCache.expires_at = time.monotonic() + DATA_AS_OF_TTL_SECONDS


def reset_data_as_of_cache() -> None:
    """Esquece o valor em memória; a próxima leitura consulta a tabela."""
    _DataAsOfCache.value = None
    _DataAsOfCache.expires_at = 0.0


async def get_last_refresh_timestamp(
    session: AsyncSession,
) -> Optional[datetime]:
    """Momento do último refresh das MVs de busca.

    Lê `max(refreshed_at)` de `mv_refresh_metadata`, com cache em memória
    de `DATA_AS_OF_TTL_SECONDS`. Falhas de leitura devolvem `None`.
    """
    now = time.monotonic()
    if now < _DataAsOfCache.expires_at:
        return _DataAsOfCache.value
    try:
        value = (
            await session.execute(
                text('SELECT max(refreshed_at) FROM mv_refresh_metadata')
            )
        ).scalar()
    except SQLAlchemyError:
        await session.rollback()
        value = None
    _DataAsOfCache.value = value
    _DataAsOfCache.expires_at = now + DATA_AS_OF_TTL_SECONDS
    return value
