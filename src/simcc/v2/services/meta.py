"""Montagem do bloco `meta` comum às respostas v2."""

import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.schemas.envelope import Meta
from simcc.v2.services import mv_refresh_service


async def build_meta(
    session: AsyncSession, start_time: float, cached: bool = False
) -> Meta:
    """`meta` com o tempo desde `start_time` (de `time.perf_counter()`)."""
    return Meta(
        took_ms=int((time.perf_counter() - start_time) * 1000),
        cached=cached,
        timestamp=datetime.now(timezone.utc),
        data_as_of=await mv_refresh_service.get_last_refresh_timestamp(
            session
        ),
    )
