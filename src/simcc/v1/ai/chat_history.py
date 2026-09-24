import logging
from typing import List, Optional

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    BaseMessage,
    messages_from_dict,
    messages_to_dict,
)

from simcc.core.cache import CacheService

logger = logging.getLogger(__name__)


class SIMCCChatMessageHistory(BaseChatMessageHistory):
    """
    Implementação oficial compatível com LangChain BaseChatMessageHistory.
    Armazena histórico de mensagens com suporte a Redis e fallback em memória.
    """

    def __init__(
        self,
        session_id: str,
        cache_service: Optional[CacheService] = None,
        max_messages: int = 10,
    ):
        self.session_id = session_id
        self.cache_service = cache_service
        self.max_messages = max_messages
        self._in_memory_messages: List[BaseMessage] = []

    @property
    def messages(self) -> List[BaseMessage]:
        return list(self._in_memory_messages)

    def add_message(self, message: BaseMessage) -> None:
        self._in_memory_messages.append(message)
        if len(self._in_memory_messages) > self.max_messages:
            self._in_memory_messages = self._in_memory_messages[
                -self.max_messages :
            ]

    def clear(self) -> None:
        self._in_memory_messages.clear()

    async def aget_messages(self) -> List[BaseMessage]:
        if self.cache_service and self.cache_service.enabled:
            try:
                key = self.cache_service.build_key(
                    'ai', 'chat_history', self.session_id
                )
                cached = await self.cache_service.get(key)
                if cached and isinstance(cached, list):
                    self._in_memory_messages = messages_from_dict(cached)
            except Exception as ex:
                logger.warning(
                    f'Falha ao ler histórico de mensagens do cache: {ex}'
                )
        return list(self._in_memory_messages)

    async def aadd_messages(self, messages: List[BaseMessage]) -> None:
        for msg in messages:
            self.add_message(msg)

        if self.cache_service and self.cache_service.enabled:
            try:
                key = self.cache_service.build_key(
                    'ai', 'chat_history', self.session_id
                )
                payload = messages_to_dict(self._in_memory_messages)
                await self.cache_service.set(
                    key, payload, ttl=self.cache_service.default_ttl
                )
            except Exception as ex:
                logger.warning(
                    f'Falha ao persistir histórico de mensagens no cache: {ex}'
                )

    async def aclear(self) -> None:
        self.clear()
        if self.cache_service and self.cache_service.enabled:
            try:
                key = self.cache_service.build_key(
                    'ai', 'chat_history', self.session_id
                )
                if self.cache_service.redis:
                    await self.cache_service.redis.delete(key)
            except Exception as ex:
                logger.warning(
                    f'Falha ao limpar histórico de mensagens no cache: {ex}'
                )
