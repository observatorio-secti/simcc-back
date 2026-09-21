import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from simcc.v2.schemas.researcher import MatchField, MatchType, SourceType
from simcc.v2.services.researcher_service import (
    build_response_envelope,
    list_researchers,
)

EXPECTED_PAGES_3 = 3
TARGET_PAGE_3 = 3
VECTOR_DIM = 1536
DATA_COUNT_2 = 2
RELEVANCE_ALICE = 0.89


@pytest.mark.unit
def test_build_response_envelope_pagination_math():
    start = time.perf_counter()
    params = {
        'pagination': {'page': 1, 'per_page': 20},
        'filters': {'q': None},
        'sort': {'by': 'name', 'order': 'asc'},
    }
    env = build_response_envelope(
        data=[],
        total_items=45,
        query_params=params,
        start_time=start,
    )
    assert env.pagination.total_pages == EXPECTED_PAGES_3
    assert env.pagination.has_next is True
    assert env.pagination.has_prev is False
    assert env.meta.took_ms >= 1
    assert env.meta.cached is False


@pytest.mark.unit
def test_build_response_envelope_empty_total():
    start = time.perf_counter()
    params = {
        'pagination': {'page': 1, 'per_page': 20},
        'filters': {},
        'sort': {'by': 'name', 'order': 'asc'},
    }
    env = build_response_envelope(
        data=[],
        total_items=0,
        query_params=params,
        start_time=start,
    )
    assert env.pagination.total_pages == 0
    assert env.pagination.has_next is False
    assert env.pagination.has_prev is False


@pytest.mark.unit
def test_build_response_envelope_last_page():
    start = time.perf_counter()
    params = {
        'pagination': {'page': TARGET_PAGE_3, 'per_page': 20},
        'filters': {},
        'sort': {'by': 'name', 'order': 'asc'},
    }
    env = build_response_envelope(
        data=[],
        total_items=45,
        query_params=params,
        start_time=start,
    )
    assert env.pagination.page == TARGET_PAGE_3
    assert env.pagination.total_pages == EXPECTED_PAGES_3
    assert env.pagination.has_next is False
    assert env.pagination.has_prev is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_researchers_semantic_vector_passed():
    mock_session = AsyncMock()
    mock_provider = AsyncMock()
    fake_vector = [0.1] * VECTOR_DIM
    mock_provider.get_embeddings.return_value = fake_vector

    query_params = {
        'filters': {'q': 'Inteligência Artificial'},
        'pagination': {'page': 1, 'per_page': 10},
        'sort': {'by': 'name', 'order': 'asc'},
    }

    with patch(
        'simcc.v2.services.researcher_service.fetch_researchers_v2',
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = (
            [{'name': 'Pesquisador IA 1'}, {'name': 'Pesquisador IA 2'}],
            2,
        )

        env = await list_researchers(
            session=mock_session,
            query_params=query_params,
            embeddings_provider=mock_provider,
        )

        mock_provider.get_embeddings.assert_awaited_once_with(
            'Inteligência Artificial'
        )
        mock_fetch.assert_awaited_once()
        assert mock_fetch.call_args.kwargs['embedding_vector'] == fake_vector
        assert len(env.data) == DATA_COUNT_2
        assert env.data[0].name == 'Pesquisador IA 1'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_researchers_with_matched_in():
    mock_session = AsyncMock()
    rid = str(uuid4())
    doc_id = str(uuid4())

    query_params = {
        'filters': {'q': 'Redes Neurais'},
        'pagination': {'page': 1, 'per_page': 10},
        'sort': {'by': 'name', 'order': 'asc'},
    }

    with (
        patch(
            'simcc.v2.services.researcher_service.fetch_researchers_v2',
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            'simcc.v2.services.researcher_service.fetch_matched_in_v2',
            new_callable=AsyncMock,
        ) as mock_fetch_matched,
    ):
        mock_fetch.return_value = (
            [
                {
                    'researcher_id': rid,
                    'name': 'Dra. Alice',
                    'relevance_score': 0.89,
                }
            ],
            1,
        )
        mock_fetch_matched.return_value = {
            rid: [
                {
                    'source_type': SourceType.ARTICLE,
                    'source_id': doc_id,
                    'field': MatchField.TITLE,
                    'title': 'Redes Neurais e Diagnóstico',
                    'snippet': 'Estudo sobre <mark>redes neurais</mark>',
                    'score': 0.75,
                    'match_type': MatchType.FTS,
                }
            ]
        }

        env = await list_researchers(
            session=mock_session,
            query_params=query_params,
        )

        assert len(env.data) == 1
        researcher = env.data[0]
        assert researcher.name == 'Dra. Alice'
        assert researcher.researcher_id == rid
        assert researcher.relevance_score == RELEVANCE_ALICE
        assert researcher.matched_in is not None
        assert len(researcher.matched_in) == 1
        assert researcher.matched_in[0].title == 'Redes Neurais e Diagnóstico'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_researchers_embeddings_failure_fallback():
    mock_session = AsyncMock()
    mock_provider = AsyncMock()
    mock_provider.get_embeddings.side_effect = RuntimeError('OpenAI API Error')

    query_params = {
        'filters': {'q': 'Robótica'},
        'pagination': {'page': 1, 'per_page': 10},
        'sort': {'by': 'name', 'order': 'asc'},
    }

    with patch(
        'simcc.v2.services.researcher_service.fetch_researchers_v2',
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = ([{'name': 'Pesquisador Robótica'}], 1)

        env = await list_researchers(
            session=mock_session,
            query_params=query_params,
            embeddings_provider=mock_provider,
        )

        assert mock_fetch.call_args.kwargs['embedding_vector'] is None
        assert len(env.data) == 1
        assert env.data[0].name == 'Pesquisador Robótica'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_researchers_no_q():
    mock_session = AsyncMock()
    mock_provider = AsyncMock()

    query_params = {
        'filters': {'q': None},
        'pagination': {'page': 1, 'per_page': 20},
        'sort': {'by': 'name', 'order': 'asc'},
    }

    with patch(
        'simcc.v2.services.researcher_service.fetch_researchers_v2',
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = ([], 0)

        env = await list_researchers(
            session=mock_session,
            query_params=query_params,
            embeddings_provider=mock_provider,
        )

        mock_provider.get_embeddings.assert_not_called()
        assert mock_fetch.call_args.kwargs['embedding_vector'] is None
        assert env.data == []
        assert env.pagination.total_items == 0
