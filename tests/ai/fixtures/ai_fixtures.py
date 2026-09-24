from unittest.mock import AsyncMock

import pytest

from simcc.v1.ai.providers.base import EmbeddingsProvider, LLMProvider
from simcc.v1.ai.query_planner import QueryPlan, SearchFilters


class MockLLMProvider(LLMProvider):
    async def generate(self, prompt: str, **kwargs) -> str:
        return 'Resposta simulada da MarIA para testes automatizados.'

    async def generate_stream(self, prompt: str, **kwargs):
        chunks = [
            'Resposta ',
            'simulada ',
            'da MarIA ',
            'para testes automatizados.',
        ]
        for chunk in chunks:
            yield chunk


class MockEmbeddingsProvider(EmbeddingsProvider):
    async def get_embeddings(self, text: str) -> list[float]:
        # Vetor dummy compatível com 1536 dimensões
        return [0.01] * 1536


@pytest.fixture
def mock_llm_provider():
    return MockLLMProvider()


@pytest.fixture
def mock_embeddings_provider():
    return MockEmbeddingsProvider()


@pytest.fixture
def mock_query_planner():
    planner = AsyncMock()
    planner.plan.return_value = QueryPlan(
        intent='researcher_search',
        semantic_query='inteligência artificial',
        filters=SearchFilters(institutions=['UNEB']),
    )
    return planner
