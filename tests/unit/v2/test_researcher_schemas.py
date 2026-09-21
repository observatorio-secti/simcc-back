# ruff: noqa: PLR2004
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from simcc.v2.schemas.researcher import (
    FiltersApplied,
    Meta,
    Pagination,
    Researcher,
    SearchResponse,
    Sort,
)


@pytest.mark.unit
def test_researcher_schema_valid():
    r_id = uuid4()
    researcher = Researcher(researcher_id=r_id, name='Maria Silva')
    assert researcher.researcher_id == r_id
    assert researcher.name == 'Maria Silva'


@pytest.mark.unit
def test_pagination_schema_valid():
    pag = Pagination(
        page=1,
        per_page=20,
        total_items=100,
        total_pages=5,
        has_next=True,
        has_prev=False,
    )
    assert pag.page == 1
    assert pag.total_pages == 5
    assert pag.has_next is True
    assert pag.has_prev is False


@pytest.mark.unit
def test_filters_applied_schema_defaults():
    filters = FiltersApplied()
    assert filters.q is None
    assert filters.year_start is None
    assert filters.year_end is None
    assert filters.institution_id is None
    assert filters.graduate_program_id is None


@pytest.mark.unit
def test_search_response_envelope():
    r_id = uuid4()
    now = datetime.now(timezone.utc)
    response = SearchResponse(
        data=[Researcher(researcher_id=r_id, name='Carlos Souza')],
        pagination=Pagination(
            page=1,
            per_page=10,
            total_items=1,
            total_pages=1,
            has_next=False,
            has_prev=False,
        ),
        filters_applied=FiltersApplied(q='Carlos'),
        sort=Sort(by='name', order='asc'),
        meta=Meta(took_ms=5, cached=False, timestamp=now),
    )

    data_dump = response.model_dump()
    assert len(data_dump['data']) == 1
    assert data_dump['data'][0]['name'] == 'Carlos Souza'
    assert data_dump['pagination']['total_items'] == 1
    assert data_dump['filters_applied']['q'] == 'Carlos'
    assert data_dump['sort']['by'] == 'name'
    assert data_dump['meta']['took_ms'] == 5
    assert data_dump['meta']['cached'] is False
    assert data_dump['facets'] is None
    assert data_dump['summary'] is None
