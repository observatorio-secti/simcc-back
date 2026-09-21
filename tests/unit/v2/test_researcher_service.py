# ruff: noqa: PLR2004
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from simcc.v2.services.researcher_service import search_researchers


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_researchers_service_success():
    mock_session = AsyncMock()
    r_id_1 = uuid4()
    r_id_2 = uuid4()

    mock_data = [
        {'researcher_id': r_id_1, 'name': 'Ana Silva'},
        {'researcher_id': r_id_2, 'name': 'Bruno Costa'},
    ]

    with patch(
        'simcc.v2.services.researcher_service.researcher_repo.fetch_researchers',
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = (mock_data, 50)

        response = await search_researchers(
            session=mock_session,
            q='Silva',
            page=1,
            per_page=20,
            sort_by='name',
            sort_order='asc',
        )

        assert len(response.data) == 2
        assert response.data[0].researcher_id == r_id_1
        assert response.data[0].name == 'Ana Silva'
        assert response.pagination.page == 1
        assert response.pagination.per_page == 20
        assert response.pagination.total_items == 50
        assert response.pagination.total_pages == 3
        assert response.pagination.has_next is True
        assert response.pagination.has_prev is False
        assert response.filters_applied.q == 'Silva'
        assert response.sort.by == 'name'
        assert response.sort.order == 'asc'
        assert response.meta.took_ms >= 1
        assert response.meta.cached is False

        mock_fetch.assert_called_once_with(
            session=mock_session,
            q='Silva',
            year_start=None,
            year_end=None,
            institution_id=None,
            graduate_program_id=None,
            page=1,
            per_page=20,
            sort_by='name',
            sort_order='asc',
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_researchers_service_middle_and_last_page():
    mock_session = AsyncMock()

    with patch(
        'simcc.v2.services.researcher_service.researcher_repo.fetch_researchers',
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = ([], 30)

        # Página intermediária
        resp_middle = await search_researchers(
            session=mock_session, page=2, per_page=10
        )
        assert resp_middle.pagination.page == 2
        assert resp_middle.pagination.total_pages == 3
        assert resp_middle.pagination.has_next is True
        assert resp_middle.pagination.has_prev is True

        # Última página
        resp_last = await search_researchers(
            session=mock_session, page=3, per_page=10
        )
        assert resp_last.pagination.page == 3
        assert resp_last.pagination.total_pages == 3
        assert resp_last.pagination.has_next is False
        assert resp_last.pagination.has_prev is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_researchers_service_empty_results():
    mock_session = AsyncMock()

    with patch(
        'simcc.v2.services.researcher_service.researcher_repo.fetch_researchers',
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = ([], 0)

        response = await search_researchers(
            session=mock_session, page=1, per_page=20
        )

        assert len(response.data) == 0
        assert response.pagination.total_items == 0
        assert response.pagination.total_pages == 0
        assert response.pagination.has_next is False
        assert response.pagination.has_prev is False
