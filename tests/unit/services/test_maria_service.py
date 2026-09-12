from unittest.mock import AsyncMock

import pytest

from simcc.ai.prompts.maria_prompts import MARIA_EMPTY_FALLBACK_MESSAGE
from simcc.ai.query_planner import QueryPlan, SearchFilters
from simcc.ai.schemas.maria import ChatStreamEventType
from simcc.services.maria_service import MariaService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maria_service_chat_ask_with_results(
    mock_llm_provider, mock_embeddings_provider
):
    mock_planner = AsyncMock()
    mock_planner.plan.return_value = QueryPlan(
        intent='researcher_search',
        semantic_query='inteligência artificial',
        filters=SearchFilters(institutions=['UFBA']),
    )

    mock_search = AsyncMock()
    mock_search.search_researchers_hybrid.return_value = [
        {
            'id': '1',
            'name': 'Dr. Teste',
            'institution_acronym': 'UFBA',
            'semantic_content': 'Pesquisa em IA e Visão Computacional',
        }
    ]

    service = MariaService(
        llm=mock_llm_provider, embeddings=mock_embeddings_provider
    )
    mock_session = AsyncMock()

    response = await service.chat_ask(
        session=mock_session,
        query='Quem pesquisa IA na UFBA?',
        planner=mock_planner,
        search_service=mock_search,
    )

    assert response.intent == 'researcher_search'
    assert len(response.researchers) == 1
    assert 'Resposta simulada da MarIA' in response.answer


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maria_service_chat_ask_empty_results_fallback(
    mock_embeddings_provider,
):
    mock_llm = AsyncMock()
    mock_planner = AsyncMock()
    mock_planner.plan.return_value = QueryPlan(
        intent='researcher_search',
        semantic_query='termo inexistente',
        filters=SearchFilters(),
    )

    mock_search = AsyncMock()
    mock_search.search_researchers_hybrid.return_value = []

    service = MariaService(llm=mock_llm, embeddings=mock_embeddings_provider)
    mock_session = AsyncMock()

    response = await service.chat_ask(
        session=mock_session,
        query='Pesquisa sobre algo que não existe',
        planner=mock_planner,
        search_service=mock_search,
    )

    assert response.answer == MARIA_EMPTY_FALLBACK_MESSAGE
    assert len(response.researchers) == 0
    # LLM generate não deve ser chamado quando 0 resultados forem
    # encontrados, economizando tokens e tempo
    mock_llm.generate.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maria_service_chat_ask_cache_hit(
    mock_llm_provider, mock_embeddings_provider
):
    mock_cache = AsyncMock()
    cached_payload = {
        'answer': 'Resposta vinda do cache',
        'intent': 'researcher_search',
        'filters_extracted': {'institutions': ['UFBA']},
        'researchers': [{'name': 'Dr. Cache'}],
        'productions': [],
        'sources': ['Dr. Cache (UFBA)'],
    }
    mock_cache.get.return_value = cached_payload

    service = MariaService(
        llm=mock_llm_provider,
        embeddings=mock_embeddings_provider,
        cache=mock_cache,
    )

    mock_session = AsyncMock()
    mock_planner = AsyncMock()
    mock_search = AsyncMock()

    response = await service.chat_ask(
        session=mock_session,
        query='Quem pesquisa IA na UFBA?',
        planner=mock_planner,
        search_service=mock_search,
    )

    assert response.answer == 'Resposta vinda do cache'
    mock_planner.plan.assert_not_called()
    mock_search.search_researchers_hybrid.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maria_service_chat_stream_empty_results_fallback(
    mock_embeddings_provider,
):
    mock_llm = AsyncMock()
    mock_planner = AsyncMock()
    mock_planner.plan.return_value = QueryPlan(
        intent='production_search',
        semantic_query='nave estelar',
        filters=SearchFilters(),
    )

    mock_search = AsyncMock()
    mock_search.search_productions_hybrid.return_value = []

    service = MariaService(llm=mock_llm, embeddings=mock_embeddings_provider)
    mock_session = AsyncMock()

    events = []
    async for event in service.chat_ask_stream(
        session=mock_session,
        query='Patente de propulsão de dobra',
        planner=mock_planner,
        search_service=mock_search,
        message_id='msg_test_123',
    ):
        events.append(event)

    types = [e.type for e in events]
    assert types == [
        ChatStreamEventType.METADATA,
        ChatStreamEventType.DELTA,
        ChatStreamEventType.DONE,
    ]
    delta_event = events[1]
    assert delta_event.content == MARIA_EMPTY_FALLBACK_MESSAGE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maria_service_general_question_without_db_search(
    mock_llm_provider, mock_embeddings_provider
):
    mock_planner = AsyncMock()
    mock_planner.plan.return_value = QueryPlan(
        intent='general_question',
        semantic_query='',
        filters=SearchFilters(),
    )

    mock_search = AsyncMock()
    service = MariaService(
        llm=mock_llm_provider, embeddings=mock_embeddings_provider
    )
    mock_session = AsyncMock()

    response = await service.chat_ask(
        session=mock_session,
        query='Olá! Como você pode me ajudar?',
        planner=mock_planner,
        search_service=mock_search,
    )

    assert response.intent == 'general_question'
    assert len(response.researchers) == 0
    assert len(response.productions) == 0
    assert 'Resposta simulada da MarIA' in response.answer
    mock_search.search_researchers_hybrid.assert_not_called()
    mock_search.search_productions_hybrid.assert_not_called()
