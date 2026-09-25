import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.services.mv_refresh_service import (
    refresh_search_materialized_views,
)
from simcc.v2.services.search_cache import bump_search_generation


@pytest_asyncio.fixture
def refresh_mvs(session: AsyncSession, redis_url: str):
    """Atualiza as MVs e invalida o cache, como a rotina de produção."""

    async def _refresh():
        await refresh_search_materialized_views(session, concurrently=False)
        bump_search_generation(redis_url)

    return _refresh
