"""Cache Redis das buscas v2, invalidado pelo refresh das MVs.

As chaves carregam uma "geração" (`GENERATION_KEY`). A rotina de refresh
incrementa a geração ao terminar: chaves antigas deixam de ser lidas e
expiram pelo TTL, sem varredura nem remoção explícita.
"""

import time
from typing import Any, Optional

import redis
import redis.asyncio as aioredis
from redis.exceptions import RedisError

from simcc.core.cache import CacheService
from simcc.core.logging import logger

GENERATION_KEY = 'simcc:v2:search:generation'
UNAVAILABLE_BACKOFF_SECONDS = 30.0


class SearchCache:
    # Compartilhado entre instâncias: evita pagar o timeout de conexão em
    # toda requisição enquanto o Redis estiver fora do ar.
    _unavailable_until: float = 0.0

    def __init__(self, redis_client: Optional[aioredis.Redis], ttl: int):
        self.redis = redis_client
        self.cache = CacheService(
            redis_client=redis_client,
            enabled=redis_client is not None,
            default_ttl=ttl,
        )

    async def build_key(self, context: str, params: Any) -> Optional[str]:
        """Monta a chave da geração atual, ou None se o cache não puder
        ser usado nesta requisição."""
        if self.redis is None:
            return None
        if time.monotonic() < SearchCache._unavailable_until:
            return None

        try:
            generation = await self.redis.get(GENERATION_KEY) or '0'
        except RedisError as exc:
            SearchCache._unavailable_until = (
                time.monotonic() + UNAVAILABLE_BACKOFF_SECONDS
            )
            logger.warning(
                'cache.unavailable',
                message=(
                    'Redis indisponível; cache v2 desligado temporariamente'
                ),
                category='system',
                data={'error': str(exc)},
            )
            return None

        return self.cache.build_key(
            'v2',
            f'{context}:{generation}',
            self.cache.hash_payload(params),
        )

    async def get(self, key: str) -> Optional[Any]:
        return await self.cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        await self.cache.set(key, value)


def bump_search_generation(redis_url: str) -> Optional[int]:
    """Invalida todo o cache de busca v2. Chamado após o refresh das MVs.

    Falhas são registradas e não interrompem a rotina: o cache antigo
    continua válido até expirar pelo TTL.
    """
    try:
        client = redis.Redis.from_url(
            redis_url, socket_timeout=1.0, socket_connect_timeout=1.0
        )
        with client:
            return client.incr(GENERATION_KEY)
    except RedisError as exc:
        logger.warning(
            'cache.generation_bump_failed',
            message='Falha ao invalidar o cache de busca v2',
            category='system',
            data={'error': str(exc)},
        )
        return None
