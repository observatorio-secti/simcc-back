# ruff: noqa: PLR2004
from http import HTTPStatus

import pytest

DEFAULT_PAGE_SIZE = 20


@pytest.mark.asyncio
async def test_read_single_researcher(client, researcher_factory):
    await researcher_factory()

    response = client.get('/v2/researcher')

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()['data']) == 1


@pytest.mark.asyncio
async def test_read_researchers_default_page_limit(client, researcher_factory):
    total_researchers = 25
    for _ in range(total_researchers):
        await researcher_factory()

    response = client.get('/v2/researcher')

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()['data']) == DEFAULT_PAGE_SIZE


@pytest.mark.asyncio
async def test_validation_invalid_sort_by(client):
    response = client.get('/v2/researcher?sort_by=metadata')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_validation_invalid_sort_order(client):
    response = client.get('/v2/researcher?sort_order=invalid')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_validation_year_start_greater_than_year_end(client):
    response = client.get('/v2/researcher?year_start=2025&year_end=2020')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_validation_unknown_query_param(client):
    response = client.get('/v2/researcher?unknown_field=invalid')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('param', 'value'),
    [
        ('page', 0),
        ('page', -1),
        ('per_page', 0),
        ('per_page', 101),
    ],
)
async def test_validation_invalid_pagination_params(client, param, value):
    response = client.get(f'/v2/researcher?{param}={value}')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_deterministic_pagination_with_duplicate_names(
    client, researcher_factory
):
    same_name = 'Duplicate Name Researcher'
    total = 5
    for _ in range(total):
        await researcher_factory(name=same_name)

    # Fetch page 1, 2, and 3 with per_page=2
    res_p1 = client.get(
        f'/v2/researcher?q={same_name}&page=1&per_page=2&sort_by=name'
    )
    res_p2 = client.get(
        f'/v2/researcher?q={same_name}&page=2&per_page=2&sort_by=name'
    )
    res_p3 = client.get(
        f'/v2/researcher?q={same_name}&page=3&per_page=2&sort_by=name'
    )

    assert res_p1.status_code == HTTPStatus.OK
    assert res_p2.status_code == HTTPStatus.OK
    assert res_p3.status_code == HTTPStatus.OK

    items_p1 = res_p1.json()['data']
    items_p2 = res_p2.json()['data']
    items_p3 = res_p3.json()['data']

    assert len(items_p1) == 2
    assert len(items_p2) == 2
    assert len(items_p3) == 1

    all_ids = (
        [item['researcher_id'] for item in items_p1]
        + [item['researcher_id'] for item in items_p2]
        + [item['researcher_id'] for item in items_p3]
    )
    # Ensure no duplicates and all 5 unique researchers are returned
    assert len(all_ids) == total
    assert len(set(all_ids)) == total


@pytest.mark.asyncio
async def test_sort_by_id(client, researcher_factory):
    unique_term = 'SortByIdTest'
    r1 = await researcher_factory(name=f'{unique_term} Alpha')
    r2 = await researcher_factory(name=f'{unique_term} Beta')

    res_asc = client.get(
        f'/v2/researcher?q={unique_term}&sort_by=id&sort_order=asc'
    )
    assert res_asc.status_code == HTTPStatus.OK
    body_asc = res_asc.json()
    assert body_asc['sort']['by'] == 'id'
    assert body_asc['sort']['order'] == 'asc'
    asc_ids = [item['researcher_id'] for item in body_asc['data']]
    expected_asc = sorted([str(r1.id), str(r2.id)])
    assert asc_ids == expected_asc

    res_desc = client.get(
        f'/v2/researcher?q={unique_term}&sort_by=id&sort_order=desc'
    )
    assert res_desc.status_code == HTTPStatus.OK
    body_desc = res_desc.json()
    assert body_desc['sort']['by'] == 'id'
    assert body_desc['sort']['order'] == 'desc'
    desc_ids = [item['researcher_id'] for item in body_desc['data']]
    expected_desc = sorted([str(r1.id), str(r2.id)], reverse=True)
    assert desc_ids == expected_desc


@pytest.mark.asyncio
async def test_empty_results_and_zero_metadata(client):
    response = client.get('/v2/researcher?q=NonExistentResearcherNameXYZ999')

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['data'] == []
    assert body['pagination']['total_items'] == 0
    assert body['pagination']['total_pages'] == 0
    assert body['pagination']['has_next'] is False
    assert body['pagination']['has_prev'] is False
    assert body['meta']['took_ms'] >= 0


@pytest.mark.asyncio
async def test_pagination_beyond_range(client, researcher_factory):
    unique_term = 'BeyondRangeTest'
    await researcher_factory(name=f'{unique_term} Researcher')

    # Total is 1 page. page=2 is page == total_pages + 1
    res_next_page = client.get(
        f'/v2/researcher?q={unique_term}&page=2&per_page=10'
    )
    assert res_next_page.status_code == HTTPStatus.OK
    body_next = res_next_page.json()
    assert body_next['data'] == []
    assert body_next['pagination']['has_next'] is False
    assert body_next['pagination']['has_prev'] is True

    # page=5 is far beyond total_pages + 1
    res_far = client.get(f'/v2/researcher?q={unique_term}&page=5&per_page=10')
    assert res_far.status_code == HTTPStatus.OK
    body_far = res_far.json()
    assert body_far['data'] == []
    assert body_far['pagination']['has_next'] is False
    assert body_far['pagination']['has_prev'] is False


@pytest.mark.asyncio
async def test_search_response_contract(client, researcher_factory):
    r = await researcher_factory(name='Contract Test Researcher')

    response = client.get(
        '/v2/researcher?q=Contract&page=1&per_page=10&sort_by=name&sort_order=asc'
    )
    assert response.status_code == HTTPStatus.OK
    body = response.json()

    # Data contract
    assert isinstance(body['data'], list)
    assert len(body['data']) == 1
    assert body['data'][0]['researcher_id'] == str(r.id)
    assert body['data'][0]['name'] == 'Contract Test Researcher'

    # Pagination contract
    assert body['pagination']['page'] == 1
    assert body['pagination']['per_page'] == 10
    assert body['pagination']['total_items'] >= 1
    assert body['pagination']['total_pages'] >= 1
    assert isinstance(body['pagination']['has_next'], bool)
    assert isinstance(body['pagination']['has_prev'], bool)

    # Filters applied contract
    assert body['filters_applied']['q'] == 'Contract'
    assert body['filters_applied']['year_start'] is None
    assert body['filters_applied']['year_end'] is None
    assert body['filters_applied']['institution_id'] == []
    assert body['filters_applied']['graduate_program_id'] == []

    # Sort contract
    assert body['sort']['by'] == 'name'
    assert body['sort']['order'] == 'asc'

    # Meta contract
    assert isinstance(body['meta']['took_ms'], int)
    assert body['meta']['took_ms'] >= 0
    assert body['meta']['cached'] is False
    assert 'timestamp' in body['meta']


@pytest.mark.asyncio
async def test_filter_by_name_and_institution(
    client, researcher_factory, institution_factory
):
    inst1 = await institution_factory()
    inst2 = await institution_factory()

    await researcher_factory(
        name='Alan Mathison Turing', institution_id=inst1.id
    )
    await researcher_factory(
        name='Grace Brewster Hopper', institution_id=inst2.id
    )

    # Filter by name
    res_name = client.get('/v2/researcher?q=Turing')
    assert res_name.status_code == HTTPStatus.OK
    data_name = res_name.json()['data']
    assert len(data_name) == 1
    assert 'Turing' in data_name[0]['name']

    # Filter by institution_id
    res_inst = client.get(f'/v2/researcher?institution_id={inst2.id}')
    assert res_inst.status_code == HTTPStatus.OK
    data_inst = res_inst.json()['data']
    assert len(data_inst) == 1
    assert 'Hopper' in data_inst[0]['name']
