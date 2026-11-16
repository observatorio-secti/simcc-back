import hashlib
import json
from typing import Any, Optional

import redis.asyncio as aioredis
from redis.exceptions import RedisError


class CacheService:
    def __init__(
        self,
        redis_client: Optional[aioredis.Redis] = None,
        enabled: bool = True,
        default_ttl: int = 3600,
    ):
        self.redis = redis_client
        self.enabled = enabled
        self.default_ttl = default_ttl

    def build_key(self, subsystem: str, context: str, identifier: str) -> str:
        """
        Gera uma chave canônica no formato: simcc:{subsystem}:{context}:{identifier}
        """
        clean_sub = subsystem.strip().lower()
        clean_ctx = context.strip().lower()
        return f'simcc:{clean_sub}:{clean_ctx}:{identifier}'

    def hash_payload(self, data: Any) -> str:
        """
        Gera um hash SHA-256 estável para qualquer estrutura de dados serializável em JSON.
        """
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        if not self.enabled or self.redis is None:
            return None

        try:
            val = await self.redis.get(key)
            if val is None:
                return None
            return json.loads(val)
        except (RedisError, Exception):
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        if not self.enabled or self.redis is None:
            return False

        try:
            expires = ttl if ttl is not None else self.default_ttl
            serialized = json.dumps(value, default=str)
            await self.redis.set(key, serialized, ex=expires)
            return True
        except (RedisError, Exception):
            return False

    async def delete(self, key: str) -> bool:
        if not self.enabled or self.redis is None:
            return False

        try:
            await self.redis.delete(key)
            return True
        except (RedisError, Exception):
            return False

    async def exists(self, key: str) -> bool:
        if not self.enabled or self.redis is None:
            return False

        try:
            return bool(await self.redis.exists(key))
        except (RedisError, Exception):
            return False
