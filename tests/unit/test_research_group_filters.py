from http import HTTPStatus
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from simcc import app
from simcc.core.db.database import get_async_session
from simcc.queries.research_group_query import (
    ResearchGroupCountQuery,
    ResearchGroupQuery,
)
from simcc.schemas import DefaultFilters
from simcc.services import research_group_service


class DummySession:
    pass


@pytest.mark.unit
def test_research_group_query_without_filters():
    query = ResearchGroupQuery(session=DummySession())
    sql = query.build_sql()
    assert 'AND i.id = :institution_id' not in sql
    assert 'AND rg.id = :group_id' not in sql
    assert query.params == {}


@pytest.mark.unit
def test_research_group_query_with_institution_id_filter():
    inst_id = uuid4()
    query = ResearchGroupQuery(session=DummySession())
    filters = DefaultFilters(institution_id=inst_id)
    query.apply_filters(filters)

    sql = query.build_sql()
    assert 'AND i.id = :institution_id' in sql
    assert query.params['institution_id'] == inst_id


@pytest.mark.unit
def test_research_group_query_with_institution_id_dict():
    inst_id = uuid4()
    query = ResearchGroupQuery(session=DummySession())
    query.apply_filters({'institution_id': inst_id})

    sql = query.build_sql()
    assert 'AND i.id = :institution_id' in sql
    assert query.params['institution_id'] == inst_id


@pytest.mark.unit
def test_research_group_query_with_both_filters():
    inst_id = uuid4()
    grp_id = uuid4()
    query = ResearchGroupQuery(session=DummySession())
    filters = DefaultFilters(institution_id=inst_id, group_id=grp_id)
    query.apply_filters(filters)

    sql = query.build_sql()
    assert 'AND i.id = :institution_id' in sql
    assert 'AND rg.id = :group_id' in sql
    assert query.params['institution_id'] == inst_id
    assert query.params['group_id'] == grp_id


@pytest.mark.unit
def test_research_group_query_with_pagination():
    query = ResearchGroupQuery(session=DummySession())
    filters = DefaultFilters(page=3, lenght=25)
    query.apply_pagination(filters)

    sql = query.build_sql()
    assert 'OFFSET 50 LIMIT 25' in sql
    assert 'ORDER BY rg.name' in sql


@pytest.mark.unit
def test_research_group_count_query_filters():
    inst_id = uuid4()
    query = ResearchGroupCountQuery(session=DummySession())
    filters = DefaultFilters(institution_id=inst_id)
    query.apply_filters(filters)

    sql = query.build_sql()
    assert 'AND i.id = :institution_id' in sql
    assert 'GROUP BY rg.area' in sql
    assert 'ORDER BY count DESC' in sql
    assert query.params['institution_id'] == inst_id


@pytest.mark.unit
def test_research_group_endpoint_passes_institution_id_and_pagination(
    monkeypatch,
):
    mock_session = AsyncMock()

    async def get_session_override():
        yield mock_session

    app.dependency_overrides[get_async_session] = get_session_override

    captured_filters = []

    async def mock_list_research_groups(session, filters):
        captured_filters.append(filters)
        return []

    monkeypatch.setattr(
        research_group_service,
        'list_research_groups',
        mock_list_research_groups,
    )

    page_num = 2
    items_lenght = 15
    inst_id = uuid4()
    with TestClient(app) as client:
        response = client.get(
            f'/research_group?institution_id={inst_id}&page={page_num}&lenght={items_lenght}'
        )

    app.dependency_overrides.clear()

    assert response.status_code == HTTPStatus.OK
    assert len(captured_filters) == 1
    assert str(captured_filters[0].institution_id) == str(inst_id)
    assert captured_filters[0].page == page_num
    assert captured_filters[0].lenght == items_lenght


@pytest.mark.unit
def test_research_group_chart_endpoints_pass_filters(monkeypatch):
    mock_session = AsyncMock()

    async def get_session_override():
        yield mock_session

    app.dependency_overrides[get_async_session] = get_session_override

    captured_calls = []

    async def mock_count_research_groups(session, filters=None):
        captured_calls.append(filters)
        return [{'area': 'Ciências Exatas', 'count': 10}]

    monkeypatch.setattr(
        research_group_service,
        'count_research_groups_by_area',
        mock_count_research_groups,
    )

    inst_id = uuid4()
    with TestClient(app) as client:
        res1 = client.get(f'/research_group/count?institution_id={inst_id}')
        res2 = client.get(f'/research_group/chart?institution_id={inst_id}')
        res3 = client.get(
            f'/metrics/research-group/chart?institution_id={inst_id}'
        )

    app.dependency_overrides.clear()

    assert res1.status_code == HTTPStatus.OK
    assert res2.status_code == HTTPStatus.OK
    assert res3.status_code == HTTPStatus.OK

    expected_calls = 3
    assert len(captured_calls) == expected_calls
    for call in captured_calls:
        assert str(call.institution_id) == str(inst_id)
