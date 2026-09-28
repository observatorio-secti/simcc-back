from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, List


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        pass

    @abstractmethod
    def generate_stream(
        self, prompt: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        pass


class EmbeddingsProvider(ABC):
    @abstractmethod
    async def get_embeddings(self, text: str) -> List[float]:
        pass
