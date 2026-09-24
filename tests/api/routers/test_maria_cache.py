from unittest.mock import AsyncMock

import pytest

from simcc import app
from simcc.core.cache import CacheService
from simcc.v1.ai.dependencies import (
    get_ai_search_service,
    get_cache_service,
    get_query_planner,
)


@pytest.mark.integration
def test_chat_ask_router_cache_hit(client):
    mock_cache = AsyncMock(spec=CacheService)
    mock_cache.enabled = True
    mock_cache.hash_payload.return_value = 'dummy_hash'
    mock_cache.build_key.return_value = 'simcc:ai:chat:batch:dummy_hash'
    mock_cache.get.return_value = {
        'answer': 'Resposta em Cache do Router',
        'intent': 'researcher_search',
        'filters_extracted': {},
        'researchers': [],
        'productions': [],
        'sources': [],
    }

    mock_planner = AsyncMock()
    mock_search = AsyncMock()

    app.dependency_overrides[get_cache_service] = lambda: mock_cache
    app.dependency_overrides[get_query_planner] = lambda: mock_planner
    app.dependency_overrides[get_ai_search_service] = lambda: mock_search

    try:
        response = client.post(
            '/ai/chat/ask',
            json={'query': 'Consulta cacheada', 'session_id': 'sess_cache_1'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['answer'] == 'Resposta em Cache do Router'
        mock_planner.plan.assert_not_called()
        mock_search.search_researchers_hybrid.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_cache_service, None)
        app.dependency_overrides.pop(get_query_planner, None)
        app.dependency_overrides.pop(get_ai_search_service, None)
