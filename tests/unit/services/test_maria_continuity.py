# ruff: noqa: PLR2004, PLR0914
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from simcc.ai.chat_history import SIMCCChatMessageHistory
from simcc.ai.query_planner import QueryPlan, SearchFilters
from simcc.ai.schemas.clarification import ClarificationResponse
from simcc.core.cache import CacheService
from simcc.services.maria_service import MariaService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maria_continuity_in_session(mock_embeddings_provider):
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = (
        'Eduardo Manuel possui 12 artigos publicados.'
    )

    mock_planner = AsyncMock()
    mock_search = AsyncMock()
    mock_search.search_productions_hybrid.return_value = [
        {
            'id': str(uuid4()),
            'title': 'Inteligência Artificial Aplicada',
            'type': 'ARTICLE',
            'year': 2023,
            'researcher': {
                'id': 'res-eduardo-123',
                'name': 'Eduardo Manuel de Freitas Jorge',
                'institution': 'UNEB',
            },
        }
    ]

    mock_cache = AsyncMock(spec=CacheService)
    mock_cache.enabled = True
    mock_cache.default_ttl = 3600
    mock_cache.build_key.side_effect = (
        lambda prefix, namespace, key: f'simcc:{prefix}:{namespace}:{key}'
    )
    cache_store = {}

    async def fake_get(key):
        return cache_store.get(key)

    async def fake_set(key, val, ttl=None):
        cache_store[key] = val

    mock_cache.get.side_effect = fake_get
    mock_cache.set.side_effect = fake_set

    mock_clarification = AsyncMock()
    # Turno 1: Clarificação resolvida via payload de seleção
    resolved_plan = QueryPlan(
        intent='production_search',
        semantic_query='',
        filters=SearchFilters(
            researcher_name='Eduardo Manuel de Freitas Jorge',
            researcher_ids=['res-eduardo-123'],
        ),
    )
    mock_clarification.resolve_pending_clarification.return_value = (
        resolved_plan
    )

    service = MariaService(
        llm=mock_llm,
        embeddings=mock_embeddings_provider,
        cache=mock_cache,
        clarification_manager=mock_clarification,
    )

    # Turno 1: Usuário envia a resposta de clarificação
    session_id = 'sess-continuity-test'
    resp1 = await service.chat_ask(
        session=AsyncMock(),
        query='Eduardo Manuel de Freitas Jorge',
        planner=mock_planner,
        search_service=mock_search,
        session_id=session_id,
        clarification_response=ClarificationResponse(
            field='researcher_id', value='res-eduardo-123'
        ),
    )

    assert resp1.answer == 'Eduardo Manuel possui 12 artigos publicados.'

    # Verifica que histórico registrou a seleção e a resposta
    history = service.get_chat_history(session_id)
    assert isinstance(history, SIMCCChatMessageHistory)
    msgs = await history.aget_messages()
    assert len(msgs) == 3
    assert '[Selecionado]: Eduardo Manuel de Freitas Jorge' in msgs[0].content
    assert msgs[1].content == 'Eduardo Manuel de Freitas Jorge'
    assert msgs[2].content == 'Eduardo Manuel possui 12 artigos publicados.'

    # Turno 2: Pergunta subsequente "Pode me trazer os artigos de Eduardo?"
    mock_planner.plan.return_value = QueryPlan(
        intent='production_search',
        semantic_query='artigos',
        filters=SearchFilters(
            researcher_name='Eduardo',
            production_types=['ARTICLE'],
        ),
    )
    mock_clarification.evaluate_researcher_clarification.return_value = None

    resp2 = await service.chat_ask(
        session=AsyncMock(),
        query='Pode me trazer os artigos de Eduardo?',
        planner=mock_planner,
        search_service=mock_search,
        session_id=session_id,
    )

    assert resp2 is not None
    # Verifica que planner.plan recebeu chat_history do turno anterior
    mock_planner.plan.assert_called_once()
    call_args = mock_planner.plan.call_args
    assert call_args[0][0] == 'Pode me trazer os artigos de Eduardo?'
    passed_history = call_args[1].get('chat_history')
    assert passed_history is not None
    assert len(passed_history) == 3

    # Verifica que o histórico acumulou pergunta e resposta do turno 2
    msgs_after = await history.aget_messages()
    assert len(msgs_after) == 5
    assert msgs_after[3].content == 'Pode me trazer os artigos de Eduardo?'
    assert msgs_after[4].content == (
        'Eduardo Manuel possui 12 artigos publicados.'
    )
