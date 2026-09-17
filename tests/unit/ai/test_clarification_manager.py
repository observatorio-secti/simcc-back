# ruff: noqa: PLR2004
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from simcc.ai.clarification import ClarificationManager
from simcc.ai.query_planner import QueryPlan, SearchFilters
from simcc.ai.schemas.clarification import (
    ClarificationResponse,
    ClarificationType,
)
from simcc.core.cache import CacheService
from simcc.services.researcher_matcher import ResearcherCandidate


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clarification_evaluate_no_researcher_name():
    manager = ClarificationManager()
    plan = QueryPlan(
        intent='production_search',
        semantic_query='dengue',
        filters=SearchFilters(),
    )
    result = await manager.evaluate_researcher_clarification(
        session=AsyncMock(),
        plan=plan,
        session_id='s1',
        original_query='artigos sobre dengue',
    )
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clarification_evaluate_single_high_confidence_auto_resolves():
    mock_matcher = AsyncMock()
    cand_id = str(uuid4())
    mock_matcher.find_candidates.return_value = [
        ResearcherCandidate(
            id=cand_id,
            name='Eduardo Manuel de Freitas Jorge',
            institution='UNEB',
            score=0.92,
        )
    ]

    manager = ClarificationManager(matcher=mock_matcher)
    plan = QueryPlan(
        intent='production_search',
        semantic_query='',
        filters=SearchFilters(researcher_name='Eduardo Jorge'),
    )

    result = await manager.evaluate_researcher_clarification(
        session=AsyncMock(),
        plan=plan,
        session_id='s1',
        original_query='produções de Eduardo Jorge',
    )

    # Auto-resolução: não gera payload de dúvida, vincula diretamente
    assert result is None
    assert plan.filters.researcher_ids == [cand_id]
    assert plan.filters.researcher_name == 'Eduardo Manuel de Freitas Jorge'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clarification_evaluate_ambiguity_returns_payload_and_caches():
    mock_matcher = AsyncMock()
    c1_id = str(uuid4())
    c2_id = str(uuid4())
    mock_matcher.find_candidates.return_value = [
        ResearcherCandidate(
            id=c1_id,
            name='Eduardo Manuel de Freitas Jorge',
            institution='UNEB',
            score=0.85,
        ),
        ResearcherCandidate(
            id=c2_id,
            name='Eduardo Jorge Valadares',
            institution='UFBA',
            score=0.82,
        ),
    ]

    mock_cache = AsyncMock(spec=CacheService)
    mock_cache.build_key = MagicMock(
        return_value='ai:clarification:session:s1'
    )

    manager = ClarificationManager(matcher=mock_matcher, cache=mock_cache)
    plan = QueryPlan(
        intent='production_search',
        semantic_query='',
        filters=SearchFilters(researcher_name='Eduardo Jorge'),
    )

    payload = await manager.evaluate_researcher_clarification(
        session=AsyncMock(),
        plan=plan,
        session_id='s1',
        original_query='produções de Eduardo Jorge',
    )

    assert payload is not None
    assert payload.type == ClarificationType.RESEARCHER_DISAMBIGUATION
    assert payload.field_to_bind == 'researcher_id'
    assert len(payload.options) == 2
    assert payload.options[0].id == c1_id
    assert payload.options[0].label == 'Eduardo Manuel de Freitas Jorge'
    assert payload.options[1].id == c2_id
    assert payload.options[1].label == 'Eduardo Jorge Valadares'

    # Cache foi chamado para guardar o estado
    mock_cache.set.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clarification_evaluate_single_low_confidence_asks():
    mock_matcher = AsyncMock()
    c1_id = str(uuid4())
    # Apenas 1 candidato, mas score baixo (typo severo)
    mock_matcher.find_candidates.return_value = [
        ResearcherCandidate(
            id=c1_id,
            name='Jaqueline Goes de Jesus',
            institution='UFBA',
            score=0.55,
        )
    ]

    manager = ClarificationManager(matcher=mock_matcher)
    plan = QueryPlan(
        intent='researcher_profile',
        semantic_query='',
        filters=SearchFilters(researcher_name='Jakeline'),
    )

    payload = await manager.evaluate_researcher_clarification(
        session=AsyncMock(),
        plan=plan,
        session_id='s1',
        original_query='Quem é Jakeline?',
    )

    assert payload is not None
    assert len(payload.options) == 1
    assert payload.options[0].label == 'Jaqueline Goes de Jesus'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clarification_resolve_pending_from_cache():
    key = 'ai:clarification:session:sess-123'
    mock_cache = AsyncMock(spec=CacheService)
    mock_cache.build_key = MagicMock(return_value=key)
    c1_id = str(uuid4())

    saved_state = {
        'context': {
            'plan': {
                'intent': 'production_search',
                'semantic_query': '',
                'filters': {
                    'institutions': [],
                    'production_types': ['ARTICLE'],
                    'researcher_name': 'Eduardo Jorge',
                },
            }
        },
        'options': [
            {
                'id': c1_id,
                'label': 'Eduardo Manuel de Freitas Jorge',
                'description': 'UNEB',
            }
        ],
    }
    mock_cache.get.return_value = saved_state

    manager = ClarificationManager(cache=mock_cache)
    response = ClarificationResponse(field='researcher_id', value=c1_id)

    resolved_plan = await manager.resolve_pending_clarification(
        session_id='sess-123',
        clarification_response=response,
    )

    assert resolved_plan is not None
    assert resolved_plan.intent == 'production_search'
    assert resolved_plan.filters.researcher_ids == [c1_id]
    assert (
        resolved_plan.filters.researcher_name
        == 'Eduardo Manuel de Freitas Jorge'
    )
    # Garante que chave foi limpa do cache
    mock_cache.delete.assert_called_once_with(key)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clarification_continuity_inherits_session_active_researcher():
    """Garante que se o usuário já especificou Eduardo Manuel na sessão,
    uma pergunta subsequente citando apenas 'Eduardo' reutiliza o contexto."""
    mock_cache = AsyncMock(spec=CacheService)
    mock_cache.build_key = MagicMock(
        return_value='simcc:ai:session_active_researcher:sess-cont'
    )
    mock_cache.get.return_value = {
        'id': 'res-eduardo-123',
        'name': 'Eduardo Manuel de Freitas Jorge',
    }

    manager = ClarificationManager(cache=mock_cache)
    plan = QueryPlan(
        intent='production_search',
        semantic_query='',
        filters=SearchFilters(researcher_name='Eduardo'),
    )

    payload = await manager.evaluate_researcher_clarification(
        session=AsyncMock(),
        plan=plan,
        session_id='sess-cont',
        original_query='Pode me trazer os artigos de Eduardo?',
    )

    # Não deve abrir modal/clarificação novamente
    assert payload is None
    # Deve herdar o ID e o nome completo
    assert plan.filters.researcher_ids == ['res-eduardo-123']
    assert plan.filters.researcher_name == 'Eduardo Manuel de Freitas Jorge'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clarification_auto_resolve_caches_active_researcher():
    """Garante que ao resolver com alta confiança, salva pesquisador
    ativo na sessão."""
    mock_matcher = AsyncMock()
    c1_id = str(uuid4())
    mock_matcher.find_candidates.return_value = [
        ResearcherCandidate(
            id=c1_id,
            name='Jaqueline Goes de Jesus',
            institution='UFBA',
            score=0.98,
        )
    ]

    mock_cache = AsyncMock(spec=CacheService)
    mock_cache.build_key = MagicMock(
        return_value='simcc:ai:session_active_researcher:sess-auto'
    )
    mock_cache.get.return_value = None

    manager = ClarificationManager(matcher=mock_matcher, cache=mock_cache)
    plan = QueryPlan(
        intent='researcher_profile',
        semantic_query='',
        filters=SearchFilters(researcher_name='Jaqueline Goes de Jesus'),
    )

    payload = await manager.evaluate_researcher_clarification(
        session=AsyncMock(),
        plan=plan,
        session_id='sess-auto',
        original_query='Quem é Jaqueline Goes?',
    )

    assert payload is None
    assert plan.filters.researcher_ids == [c1_id]
    mock_cache.set.assert_called_once_with(
        'simcc:ai:session_active_researcher:sess-auto',
        {'id': c1_id, 'name': 'Jaqueline Goes de Jesus'},
        ttl=1800,
    )
