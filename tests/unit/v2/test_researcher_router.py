# ruff: noqa: PLR2004
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from simcc import app
from simcc.v2 import v2_app
from simcc.v2.schemas.researcher import (
    FiltersApplied,
    Meta,
    Pagination,
    Researcher,
    SearchResponse,
    Sort,
)


@pytest.fixture
def mock_search_response():
    r_id = uuid4()
    return SearchResponse(
        data=[Researcher(researcher_id=r_id, name='Carlos Drummond')],
        pagination=Pagination(
            page=1,
            per_page=20,
            total_items=1,
            total_pages=1,
            has_next=False,
            has_prev=False,
        ),
        filters_applied=FiltersApplied(q='Drummond'),
        sort=Sort(by='name', order='asc'),
        meta=Meta(
            took_ms=4,
            cached=False,
            timestamp=datetime.now(timezone.utc),
        ),
    )


@pytest.mark.unit
def test_get_researcher_via_v2_subapp(mock_search_response):
    """Testa a chamada direta na sub-aplicação v2_app."""
    with patch(
        'simcc.v2.routers.researcher.researcher_service.search_researchers',
        new_callable=AsyncMock,
    ) as mock_service:
        mock_service.return_value = mock_search_response

        client = TestClient(v2_app)
        response = client.get('/researcher?q=Drummond')

        assert response.status_code == HTTPStatus.OK
        json_data = response.json()
        assert len(json_data['data']) == 1
        assert json_data['data'][0]['name'] == 'Carlos Drummond'
        assert json_data['pagination']['total_items'] == 1
        assert json_data['filters_applied']['q'] == 'Drummond'
        assert json_data['sort']['by'] == 'name'
        assert json_data['meta']['took_ms'] == 4


@pytest.mark.unit
def test_get_researcher_via_mounted_main_app(mock_search_response):
    """Testa o acesso através da aplicação principal montada em /v2."""
    with patch(
        'simcc.v2.routers.researcher.researcher_service.search_researchers',
        new_callable=AsyncMock,
    ) as mock_service:
        mock_service.return_value = mock_search_response

        client = TestClient(app)
        response = client.get('/v2/researcher?q=Drummond')

        assert response.status_code == HTTPStatus.OK
        json_data = response.json()
        assert len(json_data['data']) == 1
        assert json_data['data'][0]['name'] == 'Carlos Drummond'
        assert json_data['pagination']['page'] == 1


@pytest.mark.unit
def test_get_researcher_validation_errors():
    """Valida erros de validação HTTP 422 para parâmetros inválidos."""
    client = TestClient(app)

    # page < 1 deve retornar 422
    resp_page_invalid = client.get('/v2/researcher?page=0')
    assert resp_page_invalid.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # per_page > 100 deve retornar 422
    resp_per_page_invalid = client.get('/v2/researcher?per_page=150')
    assert resp_per_page_invalid.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # sort_order diferente de asc/desc deve retornar 422
    resp_sort_invalid = client.get('/v2/researcher?sort_order=invalid')
    assert resp_sort_invalid.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
