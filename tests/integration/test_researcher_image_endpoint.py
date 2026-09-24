from http import HTTPStatus
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from simcc import app
from simcc.core.db.database import get_async_session


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_researcher_image_no_params():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        response = await ac.get('/researcher/image')
    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_researcher_image_non_existent_researcher(session):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_async_session] = override_get_session
    try:
        non_existent_uuid = str(uuid4())
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url='http://test'
        ) as ac:
            response = await ac.get(
                f'/researcher/image?researcher_id={non_existent_uuid}'
            )
        assert response.status_code == HTTPStatus.NOT_FOUND
    finally:
        app.dependency_overrides.pop(get_async_session, None)
