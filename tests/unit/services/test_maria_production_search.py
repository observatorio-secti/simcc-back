from unittest.mock import AsyncMock

import pytest

from simcc.v1.ai.query_planner import QueryPlan, SearchFilters
from simcc.v1.services.maria_service import MariaService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_ask_production_search(
    mock_llm_provider, mock_embeddings_provider
):
    """
    Testa se o MariaService orquestra corretamente o QueryPlanner e o
    search_productions_hybrid quando a intenção é 'production_search'.
    """
    service = MariaService(
        llm=mock_llm_provider, embeddings=mock_embeddings_provider
    )

    planner = AsyncMock()
    planner.plan.return_value = QueryPlan(
        intent='production_search',
        semantic_query='leishmaniose',
        filters=SearchFilters(production_types=['ARTICLE']),
    )

    search_service = AsyncMock()
    search_service.search_productions_hybrid.return_value = [
        {
            'id': 'prod-123',
            'type': 'ARTICLE',
            'title': 'Estudo imunológico sobre leishmaniose',
            'year': '2023',
            'authors': 'Claudia Ida Brodskyn',
            'doi': '10.1016/j.test.2023',
            'details': {'periodical': 'Journal of Immunology', 'qualis': 'A1'},
            'researcher': {
                'id': 'r-1',
                'name': 'Claudia Ida Brodskyn',
                'institution': 'UFBA',
            },
        }
    ]

    session = AsyncMock()

    response = await service.chat_ask(
        session=session,
        query='Quais artigos foram publicados sobre leishmaniose?',
        planner=planner,
        search_service=search_service,
    )

    # Assert
    assert response.intent == 'production_search'
    assert response.filters_extracted['production_types'] == ['ARTICLE']
    assert len(response.productions) == 1
    assert (
        response.productions[0]['title']
        == 'Estudo imunológico sobre leishmaniose'
    )
    assert response.productions[0]['doi'] == '10.1016/j.test.2023'
    assert len(response.sources) >= 1
    assert len(response.answer) > 0

    search_service.search_productions_hybrid.assert_called_once_with(
        session=session,
        query='leishmaniose',
        limit=10,
        filters={'institutions': [], 'production_types': ['ARTICLE']},
    )
