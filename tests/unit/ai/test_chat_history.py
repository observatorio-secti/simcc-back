# ruff: noqa: PLR2004
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from simcc.core.cache import CacheService
from simcc.v1.ai.chat_history import SIMCCChatMessageHistory


@pytest.mark.unit
def test_chat_history_in_memory_sync():
    history = SIMCCChatMessageHistory(session_id='test-sess', max_messages=3)
    assert history.messages == []

    history.add_message(HumanMessage(content='Msg 1'))
    history.add_message(AIMessage(content='Msg 2'))
    history.add_message(HumanMessage(content='Msg 3'))
    history.add_message(AIMessage(content='Msg 4'))

    # Window capped to max_messages (3)
    assert len(history.messages) == 3
    assert history.messages[0].content == 'Msg 2'
    assert history.messages[1].content == 'Msg 3'
    assert history.messages[2].content == 'Msg 4'

    history.clear()
    assert history.messages == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_history_async_in_memory():
    history = SIMCCChatMessageHistory(session_id='test-sess', max_messages=5)

    await history.aadd_messages([
        HumanMessage(content='Oi'),
        AIMessage(content='Olá! Como posso ajudar?'),
    ])

    msgs = await history.aget_messages()
    assert len(msgs) == 2
    assert msgs[0].content == 'Oi'
    assert msgs[1].content == 'Olá! Como posso ajudar?'

    await history.aclear()
    assert await history.aget_messages() == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_history_with_cache_persistence():
    mock_cache = AsyncMock(spec=CacheService)
    mock_cache.enabled = True
    mock_cache.default_ttl = 3600
    mock_cache.build_key = MagicMock(
        return_value='simcc:ai:chat_history:sess-cache'
    )
    mock_cache.get.return_value = None

    history = SIMCCChatMessageHistory(
        session_id='sess-cache',
        cache_service=mock_cache,
        max_messages=10,
    )

    await history.aadd_messages([
        HumanMessage(content='Pergunta 1'),
        AIMessage(content='Resposta 1'),
    ])

    mock_cache.set.assert_called_once()
    args, kwargs = mock_cache.set.call_args
    assert args[0] == 'simcc:ai:chat_history:sess-cache'
    assert len(args[1]) == 2
    assert args[1][0]['type'] == 'human'
    assert args[1][0]['data']['content'] == 'Pergunta 1'

    # Simula carregamento a partir do cache
    mock_cache.get.return_value = [
        {'type': 'human', 'data': {'content': 'Pergunta 1'}},
        {'type': 'ai', 'data': {'content': 'Resposta 1'}},
    ]

    restored_msgs = await history.aget_messages()
    assert len(restored_msgs) == 2
    assert restored_msgs[0].content == 'Pergunta 1'
    assert restored_msgs[1].content == 'Resposta 1'
