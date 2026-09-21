# ruff: noqa: PLR2004
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from simcc.v2.schemas import (
    BaseFilter,
    BaseTemporalFilter,
    GraduateProgramFilter,
    InstitutionFilter,
    ProductionFilter,
    ResearcherFilter,
)
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
def test_unified_filter_schemas_defaults():
    base = BaseFilter()
    assert base.q is None

    temporal = BaseTemporalFilter(q='IA', year_start=2020, year_end=2024)
    assert temporal.q == 'IA'
    assert temporal.year_start == 2020
    assert temporal.year_end == 2024

    r_id = uuid4()
    inst_id = uuid4()
    gp_id = uuid4()

    rf = ResearcherFilter(
        q='Carlos', institution_id=inst_id, graduate_program_id=gp_id
    )
    assert rf.q == 'Carlos'
    assert rf.institution_id == inst_id
    assert rf.graduate_program_id == gp_id

    pf = ProductionFilter(
        q='Redes Neurais',
        year_start=2019,
        year_end=2023,
        researcher_id=r_id,
        type='ARTIGO',
        qualis='A1',
        magazine='IEEE',
    )
    assert pf.type == 'ARTIGO'
    assert pf.qualis == 'A1'
    assert pf.magazine == 'IEEE'
    assert pf.researcher_id == r_id

    inf = InstitutionFilter(q='UFBA', state='BA', city='Salvador')
    assert inf.q == 'UFBA'
    assert inf.state == 'BA'
    assert inf.city == 'Salvador'

    gpf = GraduateProgramFilter(
        q='Ciência da Computação',
        area='Exatas',
        modality='ACADÊMICO',
        rating='5',
    )
    assert gpf.q == 'Ciência da Computação'
    assert gpf.area == 'Exatas'
    assert gpf.modality == 'ACADÊMICO'
    assert gpf.rating == '5'


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
        filters_applied=ResearcherFilter(q='Carlos'),
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
