from collections.abc import AsyncIterator
from typing import Any, List, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from simcc.v1.ai.exceptions import AIServiceUnavailableException
from simcc.v1.ai.providers.base import EmbeddingsProvider, LLMProvider


class OpenAIProvider(LLMProvider, EmbeddingsProvider):
    def __init__(
        self, api_key: Optional[str] = None, model: str = 'gpt-4o-mini'
    ):
        self.api_key = api_key
        self.model = model

        if self.api_key:
            self.llm = ChatOpenAI(
                api_key=self.api_key, model=model, temperature=0.7
            )
            self.embeddings = OpenAIEmbeddings(
                api_key=self.api_key, model='text-embedding-3-small'
            )
        else:
            self.llm = None
            self.embeddings = None

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        if not self.llm:
            raise AIServiceUnavailableException()
        response = await self.llm.ainvoke(prompt)
        return str(response.content)

    async def generate_stream(
        self, prompt: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        if not self.llm:
            raise AIServiceUnavailableException()
        async for chunk in self.llm.astream(prompt):
            if chunk.content:
                yield str(chunk.content)

    async def get_embeddings(self, text: str) -> List[float]:
        if not self.embeddings:
            raise AIServiceUnavailableException()
        return await self.embeddings.aembed_query(text)
