from unittest.mock import AsyncMock

import pytest

from simcc import app
from simcc.v1.ai.dependencies import get_ai_search_service
from simcc.v1.ai.prompts.maria_prompts import MARIA_EMPTY_FALLBACK_MESSAGE


@pytest.mark.integration
def test_chat_ask_router_cutoff_empty_results(client):
    mock_search = AsyncMock()
    mock_search.search_researchers_hybrid.return_value = []
    mock_search.search_productions_hybrid.return_value = []

    app.dependency_overrides[get_ai_search_service] = lambda: mock_search

    try:
        response = client.post(
            '/ai/chat/ask',
            json={
                'query': 'Tema sem correspondência ou abaixo da linha de corte'
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data['answer'] == MARIA_EMPTY_FALLBACK_MESSAGE
        assert data['researchers'] == []
        assert data['productions'] == []
    finally:
        app.dependency_overrides.pop(get_ai_search_service, None)
