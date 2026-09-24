import pytest

from simcc import app
from simcc.v1.ai.dependencies import (
    get_embeddings_provider,
    get_llm_provider,
    get_query_planner,
)
from simcc.v1.ai.providers.openai_provider import OpenAIProvider
from simcc.v1.ai.query_planner import QueryPlanner


@pytest.mark.integration
def test_chat_ask_without_openai_api_key(client):
    # Provider and planner initialized with no key (None)
    provider_no_key = OpenAIProvider(api_key=None)
    planner_no_key = QueryPlanner(api_key=None)

    app.dependency_overrides[get_llm_provider] = lambda: provider_no_key
    app.dependency_overrides[get_embeddings_provider] = lambda: provider_no_key
    app.dependency_overrides[get_query_planner] = lambda: planner_no_key

    try:
        response = client.post(
            '/ai/chat/ask',
            json={'query': 'Pergunta sem chave de API configurada'},
        )
        assert response.status_code == 503
        data = response.json()
        assert 'detail' in data
        assert 'temporariamente indisponível' in data['detail']
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)
        app.dependency_overrides.pop(get_embeddings_provider, None)
        app.dependency_overrides.pop(get_query_planner, None)
