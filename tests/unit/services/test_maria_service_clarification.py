from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from simcc.v1.ai.query_planner import QueryPlan, SearchFilters
from simcc.v1.ai.schemas.clarification import (
    ClarificationOption,
    ClarificationPayload,
    ClarificationResponse,
    ClarificationType,
)
from simcc.v1.ai.schemas.maria import ChatStreamEventType
from simcc.v1.services.maria_service import MariaService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_ask_returns_clarification_without_synthesis(
    mock_llm_provider, mock_embeddings_provider
):
    mock_planner = AsyncMock()
    mock_planner.plan.return_value = QueryPlan(
        intent='production_search',
        semantic_query='',
        filters=SearchFilters(researcher_name='Eduardo Jorge'),
    )

    cand_id = str(uuid4())
    mock_clarification_manager = AsyncMock()
    payload = ClarificationPayload(
        type=ClarificationType.RESEARCHER_DISAMBIGUATION,
        question='Qual Eduardo Jorge você deseja consultar?',
        field_to_bind='researcher_id',
        options=[
            ClarificationOption(
                id=cand_id,
                label='Eduardo Manuel de Freitas Jorge',
                description='UNEB',
            )
        ],
        original_query='produções de Eduardo Jorge',
    )
    mock_clarification_manager.evaluate_researcher_clarification.return_value = payload

    mock_llm = AsyncMock()
    mock_search = AsyncMock()
    service = MariaService(
        llm=mock_llm,
        embeddings=mock_embeddings_provider,
        clarification_manager=mock_clarification_manager,
    )

    response = await service.chat_ask(
        session=AsyncMock(),
        query='produções de Eduardo Jorge',
        planner=mock_planner,
        search_service=mock_search,
        session_id='sess_test',
    )

    assert response.clarification is not None
    assert response.clarification.field_to_bind == 'researcher_id'
    assert (
        response.clarification.question
        == 'Qual Eduardo Jorge você deseja consultar?'
    )
    # Não deve chamar o LLM nem a busca de produções
    mock_llm.generate.assert_not_called()
    mock_search.search_productions_hybrid.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_ask_stream_emits_clarification_event(
    mock_llm_provider, mock_embeddings_provider
):
    mock_planner = AsyncMock()
    mock_planner.plan.return_value = QueryPlan(
        intent='production_search',
        semantic_query='',
        filters=SearchFilters(researcher_name='Eduardo Jorge'),
    )

    cand_id = str(uuid4())
    mock_clarification_manager = AsyncMock()
    payload = ClarificationPayload(
        type=ClarificationType.RESEARCHER_DISAMBIGUATION,
        question='Qual Eduardo Jorge?',
        field_to_bind='researcher_id',
        options=[
            ClarificationOption(
                id=cand_id,
                label='Eduardo Manuel de Freitas Jorge',
                description='UNEB',
            )
        ],
        original_query='produções de Eduardo Jorge',
    )
    mock_clarification_manager.evaluate_researcher_clarification.return_value = payload

    mock_search = AsyncMock()
    service = MariaService(
        llm=mock_llm_provider,
        embeddings=mock_embeddings_provider,
        clarification_manager=mock_clarification_manager,
    )

    events = []
    async for event in service.chat_ask_stream(
        session=AsyncMock(),
        query='produções de Eduardo Jorge',
        planner=mock_planner,
        search_service=mock_search,
        message_id='msg_test',
    ):
        events.append(event)

    types = [e.type for e in events]
    assert ChatStreamEventType.CLARIFICATION in types
    assert ChatStreamEventType.DONE in types

    clarification_ev = next(
        e for e in events if e.type == ChatStreamEventType.CLARIFICATION
    )
    assert clarification_ev.clarification is not None
    assert clarification_ev.clarification.field_to_bind == 'researcher_id'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_ask_stream_resolves_clarification_and_runs_search(
    mock_llm_provider, mock_embeddings_provider
):
    cand_id = str(uuid4())
    mock_clarification_manager = AsyncMock()
    resolved_plan = QueryPlan(
        intent='production_search',
        semantic_query='',
        filters=SearchFilters(
            researcher_name='Eduardo Manuel de Freitas Jorge',
            researcher_ids=[cand_id],
        ),
    )
    mock_clarification_manager.resolve_pending_clarification.return_value = (
        resolved_plan
    )

    mock_search = AsyncMock()
    mock_search.search_productions_hybrid.return_value = [
        {
            'id': 'prod-1',
            'type': 'ARTICLE',
            'title': 'Inteligência Artificial na Saúde',
            'year': '2023',
            'authors': 'Eduardo Manuel de Freitas Jorge',
            'researcher': {
                'id': cand_id,
                'name': 'Eduardo Manuel de Freitas Jorge',
                'institution': 'UNEB',
            },
        }
    ]

    service = MariaService(
        llm=mock_llm_provider,
        embeddings=mock_embeddings_provider,
        clarification_manager=mock_clarification_manager,
    )

    clarification_resp = ClarificationResponse(
        field='researcher_id', value=cand_id
    )
    events = []
    async for event in service.chat_ask_stream(
        session=AsyncMock(),
        query='Eduardo Manuel de Freitas Jorge',
        planner=AsyncMock(),
        search_service=mock_search,
        message_id='msg_resume',
        clarification_response=clarification_resp,
    ):
        events.append(event)

    types = [e.type for e in events]
    assert ChatStreamEventType.METADATA in types
    assert ChatStreamEventType.DELTA in types
    assert ChatStreamEventType.DONE in types

    # A busca híbrida de produções foi chamada com o researcher_ids resolvido
    mock_search.search_productions_hybrid.assert_called_once()
