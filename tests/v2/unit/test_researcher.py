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
