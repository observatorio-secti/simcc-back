from http import HTTPStatus
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from simcc import app
from simcc.ai.dependencies import get_embeddings_provider
from simcc.core.db.database import get_async_session

DEFAULT_PER_PAGE = 20
PAGE_TWO = 2
PER_PAGE_TWO = 2
TOTAL_ITEMS_15 = 15
TOTAL_PAGES_8 = 8
YEAR_START_2021 = 2021
YEAR_END_2023 = 2023
RELEVANCE_SCORE_TEST = 0.847


@pytest.fixture
def v2_client():
    mock_session = AsyncMock()
    mock_embeddings = AsyncMock()
    mock_embeddings.get_embeddings.return_value = [0.0] * 1536

    async def get_session_override():
        yield mock_session

    app.dependency_overrides[get_async_session] = get_session_override
    app.dependency_overrides[get_embeddings_provider] = lambda: mock_embeddings

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.unit
def test_get_v2_researcher_contract(v2_client):
    with patch(
        'simcc.v2.services.researcher_service.fetch_researchers_v2',
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = (
            [
                {
                    'researcher_id': '11111111-1111-1111-1111-111111111111',
                    'name': 'Nome do Pesquisador',
                    'relevance_score': None,
                }
            ],
            1,
        )

        response = v2_client.get('/v2/researcher')
        assert response.status_code == HTTPStatus.OK
        payload = response.json()

        # Validação da estrutura estrita do contrato solicitado
        assert 'data' in payload
        assert 'pagination' in payload
        assert 'filters_applied' in payload
        assert 'sort' in payload
        assert 'meta' in payload

        # data
        assert len(payload['data']) == 1
        item = payload['data'][0]
        assert item['name'] == 'Nome do Pesquisador'
        assert item['researcher_id'] == '11111111-1111-1111-1111-111111111111'
        assert item['relevance_score'] is None
        assert item['matched_in'] is None
        assert 'institution_acronym' not in item

        # pagination
        assert payload['pagination']['page'] == 1
        assert payload['pagination']['per_page'] == DEFAULT_PER_PAGE
        assert payload['pagination']['total_items'] == 1
        assert payload['pagination']['total_pages'] == 1
        assert payload['pagination']['has_next'] is False
        assert payload['pagination']['has_prev'] is False

        # filters_applied
        assert payload['filters_applied']['year_start'] is None
        assert payload['filters_applied']['year_end'] is None
        assert payload['filters_applied']['institution_id'] is None
        assert payload['filters_applied']['graduate_program_id'] is None
        assert payload['filters_applied']['q'] is None

        # sort
        assert payload['sort']['by'] == 'name'
        assert payload['sort']['order'] == 'asc'

        # meta
        assert payload['meta']['cached'] is False
        assert isinstance(payload['meta']['took_ms'], int)
        assert 'timestamp' in payload['meta']


@pytest.mark.unit
def test_get_v2_researcher_with_matched_in_and_relevance(v2_client):
    rid = str(uuid4())
    doc_id = str(uuid4())

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
                    'name': 'Gleidson Costa',
                    'relevance_score': 0.847,
                }
            ],
            1,
        )
        mock_fetch_matched.return_value = {
            rid: [
                {
                    'source_type': 'ARTICLE',
                    'source_id': doc_id,
                    'field': 'abstract',
                    'title': 'Deep Learning aplications',
                    'snippet': 'modelos de <mark>aprendizado profundo</mark>',
                    'score': 0.62,
                    'match_type': 'fts',
                }
            ]
        }

        response = v2_client.get('/v2/researcher?q=aprendizado+profundo')
        assert response.status_code == HTTPStatus.OK
        payload = response.json()

        assert len(payload['data']) == 1
        res = payload['data'][0]
        assert res['name'] == 'Gleidson Costa'
        assert res['relevance_score'] == RELEVANCE_SCORE_TEST
        assert 'institution_acronym' not in res
        assert res['matched_in'] is not None
        assert len(res['matched_in']) == 1
        assert res['matched_in'][0]['source_type'] == 'ARTICLE'
        assert res['matched_in'][0]['field'] == 'abstract'
        assert res['matched_in'][0]['match_type'] == 'fts'


@pytest.mark.unit
def test_get_v2_researcher_with_filters_and_pagination(v2_client):
    inst_id = uuid4()
    gp_id = uuid4()

    with patch(
        'simcc.v2.services.researcher_service.fetch_researchers_v2',
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = (
            [
                {
                    'researcher_id': str(uuid4()),
                    'name': 'Pesquisador 1',
                    'relevance_score': None,
                },
                {
                    'researcher_id': str(uuid4()),
                    'name': 'Pesquisador 2',
                    'relevance_score': None,
                },
            ],
            TOTAL_ITEMS_15,
        )

        url = (
            f'/v2/researcher?page={PAGE_TWO}&per_page={PER_PAGE_TWO}'
            f'&by=name&order=desc'
            f'&year_start={YEAR_START_2021}&year_end={YEAR_END_2023}'
            f'&institution_id={inst_id}'
            f'&graduate_program_id={gp_id}&q=ciencia'
        )
        response = v2_client.get(url)
        assert response.status_code == HTTPStatus.OK
        payload = response.json()

        assert len(payload['data']) == PER_PAGE_TWO
        assert payload['pagination']['page'] == PAGE_TWO
        assert payload['pagination']['per_page'] == PER_PAGE_TWO
        assert payload['pagination']['total_items'] == TOTAL_ITEMS_15
        assert payload['pagination']['total_pages'] == TOTAL_PAGES_8
        assert payload['pagination']['has_next'] is True
        assert payload['pagination']['has_prev'] is True

        assert payload['filters_applied']['year_start'] == YEAR_START_2021
        assert payload['filters_applied']['year_end'] == YEAR_END_2023
        assert payload['filters_applied']['institution_id'] == str(inst_id)
        assert payload['filters_applied']['graduate_program_id'] == str(gp_id)
        assert payload['filters_applied']['q'] == 'ciencia'

        assert payload['sort']['by'] == 'name'
        assert payload['sort']['order'] == 'desc'


@pytest.mark.unit
def test_get_v2_researcher_query_alias(v2_client):
    with patch(
        'simcc.v2.services.researcher_service.fetch_researchers_v2',
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = ([], 0)

        response = v2_client.get('/v2/researcher?query=computacao')
        assert response.status_code == HTTPStatus.OK
        payload = response.json()
        assert payload['filters_applied']['q'] == 'computacao'


@pytest.mark.unit
def test_get_v2_researcher_validation_errors(v2_client):
    # page < 1
    resp = v2_client.get('/v2/researcher?page=0')
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # per_page > 100
    resp = v2_client.get('/v2/researcher?per_page=101')
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # invalid sort order
    resp = v2_client.get('/v2/researcher?order=invalid')
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
