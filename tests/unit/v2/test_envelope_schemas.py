from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from simcc.v2.schemas.envelope import (
    PaginationMetadata,
    ResponseEnvelope,
    ResponseMeta,
    SortMetadata,
)
from simcc.v2.schemas.researcher import (
    MatchedInItem,
    MatchField,
    MatchType,
    ResearcherV2,
    SourceType,
)

EXPECTED_PAGES = 3
TOOK_MS_TEST = 12
TEST_RELEVANCE_SCORE = 0.92


@pytest.mark.unit
def test_researcher_v2_schema_simple():
    researcher = ResearcherV2(name='Maria Silva')
    assert researcher.name == 'Maria Silva'
    assert researcher.researcher_id is None
    assert researcher.relevance_score is None
    assert researcher.matched_in is None
    # Garante que institution_acronym foi mantido de fora conforme solicitado
    assert not hasattr(researcher, 'institution_acronym')


@pytest.mark.unit
def test_researcher_v2_schema_with_matched_in():
    r_id = uuid4()
    s_id = uuid4()
    item = MatchedInItem(
        source_type=SourceType.ARTICLE,
        source_id=s_id,
        field=MatchField.ABSTRACT,
        title='Machine Learning in Health',
        snippet='...models of <mark>machine learning</mark>...',
        score=0.85,
        match_type=MatchType.FTS,
    )
    researcher = ResearcherV2(
        researcher_id=r_id,
        name='Carlos Lima',
        relevance_score=TEST_RELEVANCE_SCORE,
        matched_in=[item],
    )
    assert researcher.researcher_id == r_id
    assert researcher.relevance_score == TEST_RELEVANCE_SCORE
    assert len(researcher.matched_in) == 1
    assert researcher.matched_in[0].source_type == SourceType.ARTICLE
    assert researcher.matched_in[0].field == MatchField.ABSTRACT
    assert researcher.matched_in[0].match_type == MatchType.FTS


@pytest.mark.unit
def test_pagination_metadata_valid():
    pag = PaginationMetadata(
        page=1,
        per_page=20,
        total_items=45,
        total_pages=EXPECTED_PAGES,
        has_next=True,
        has_prev=False,
    )
    assert pag.page == 1
    assert pag.total_pages == EXPECTED_PAGES
    assert pag.has_next is True
    assert pag.has_prev is False


@pytest.mark.unit
def test_pagination_metadata_validation_error():
    with pytest.raises(ValidationError):
        PaginationMetadata(
            page=0,  # ge=1 violated
            per_page=20,
            total_items=10,
            total_pages=1,
            has_next=False,
            has_prev=False,
        )


@pytest.mark.unit
def test_sort_metadata():
    sort = SortMetadata(by='name', order='asc')
    assert sort.by == 'name'
    assert sort.order == 'asc'

    sort_desc = SortMetadata(by='name', order='desc')
    assert sort_desc.order == 'desc'

    with pytest.raises(ValidationError):
        SortMetadata(by='name', order='invalid_order')


@pytest.mark.unit
def test_response_envelope_complete():
    now = datetime.now(timezone.utc)
    envelope = ResponseEnvelope[ResearcherV2](
        data=[ResearcherV2(name='Pesquisador Exemplo')],
        pagination=PaginationMetadata(
            page=1,
            per_page=20,
            total_items=1,
            total_pages=1,
            has_next=False,
            has_prev=False,
        ),
        filters_applied={'year_start': None, 'year_end': None, 'q': None},
        sort=SortMetadata(by='name', order='asc'),
        meta=ResponseMeta(
            took_ms=TOOK_MS_TEST,
            cached=False,
            timestamp=now,
        ),
    )

    dumped = envelope.model_dump(mode='json')
    assert dumped['data'][0]['name'] == 'Pesquisador Exemplo'
    assert dumped['data'][0]['matched_in'] is None
    assert 'institution_acronym' not in dumped['data'][0]
    assert dumped['pagination']['page'] == 1
    assert dumped['pagination']['total_items'] == 1
    assert dumped['sort']['by'] == 'name'
    assert dumped['meta']['took_ms'] == TOOK_MS_TEST
    assert dumped['meta']['cached'] is False
    assert dumped['meta']['timestamp'] == now.isoformat().replace(
        '+00:00', 'Z'
    )
