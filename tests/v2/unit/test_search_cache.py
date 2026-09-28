# ruff: noqa: PLR2004
import uuid
from http import HTTPStatus

import pytest
import redis
import redis.asyncio as aioredis
from sqlalchemy import event

from simcc import app
from simcc.core.cache import redis_client
from simcc.core.dependencies import get_settings
from simcc.core.settings import Settings
from simcc.v2.dependencies import get_search_cache
from simcc.v2.services.mv_refresh_service import (
    refresh_search_materialized_views,
)
from simcc.v2.services.search_cache import (
    GENERATION_KEY,
    SearchCache,
    bump_search_generation,
)
from tests.factories.researcher import ResearcherFactory

TTL = 60  # mesmo valor do fixture `cache`


@pytest.fixture
def query_counter(engine):
    statements = []

    def count(*args, **kwargs):
        statement = args[2] if len(args) > 2 else kwargs.get('statement', '')
        if statement.strip().upper().startswith(('SELECT', 'WITH')):
            statements.append(statement)

    event.listen(engine.sync_engine, 'before_cursor_execute', count)
    yield statements
    event.remove(engine.sync_engine, 'before_cursor_execute', count)


@pytest.mark.asyncio
async def test_second_request_is_served_from_cache(
    client, researcher_factory, query_counter
):
    await researcher_factory(name='Cache Pesquisador')
    url = '/v2/researcher?q=Cache&facets=institution'

    first = client.get(url).json()
    query_counter.clear()
    second = client.get(url).json()

    assert first['meta']['cached'] is False
    assert second['meta']['cached'] is True
    assert query_counter == []
    for field in ('data', 'pagination', 'facets', 'sort', 'filters_applied'):
        assert second[field] == first[field]


@pytest.mark.asyncio
async def test_cache_key_has_ttl(client, redis_url, researcher_factory):
    await researcher_factory()
    client.get('/v2/researcher')

    client = redis.Redis.from_url(redis_url)
    keys = [
        k for k in client.keys('simcc:v2:*') if k != GENERATION_KEY.encode()
    ]
    assert len(keys) == 1
    assert 0 < client.ttl(keys[0]) <= TTL


@pytest.mark.asyncio
async def test_different_params_use_different_entries(
    client, researcher_factory
):
    await researcher_factory()

    client.get('/v2/researcher?page=1')
    response = client.get('/v2/researcher?page=2')

    assert response.json()['meta']['cached'] is False


@pytest.mark.asyncio
async def test_list_param_order_shares_entry_but_echoes_request(
    client, institution_factory, researcher_factory
):
    inst_a = await institution_factory()
    inst_b = await institution_factory()
    await researcher_factory(institution_id=inst_a.id)

    client.get(
        f'/v2/researcher?institution_id={inst_a.id}&institution_id={inst_b.id}'
    )
    response = client.get(
        f'/v2/researcher?institution_id={inst_b.id}&institution_id={inst_a.id}'
    ).json()

    assert response['meta']['cached'] is True
    assert response['filters_applied']['institution_id'] == [
        str(inst_b.id),
        str(inst_a.id),
    ]


@pytest.mark.asyncio
async def test_generation_bump_invalidates(
    client, session, redis_url, researcher_factory
):
    await researcher_factory(name='Antes Refresh')
    client.get('/v2/researcher')

    # Dados e MVs mudam, mas sem invalidar: a resposta antiga continua
    session.add(ResearcherFactory(name='Depois Refresh'))
    await session.commit()
    await refresh_search_materialized_views(session)
    stale = client.get('/v2/researcher').json()
    assert stale['meta']['cached'] is True
    assert stale['pagination']['total_items'] == 1

    bump_search_generation(redis_url)

    fresh = client.get('/v2/researcher').json()
    assert fresh['meta']['cached'] is False
    assert fresh['pagination']['total_items'] == 2


@pytest.mark.asyncio
async def test_refresh_mvs_fixture_invalidates_like_production(
    client, researcher_factory
):
    await researcher_factory(name='Primeiro')
    client.get('/v2/researcher')

    await researcher_factory(name='Segundo')
    response = client.get('/v2/researcher').json()

    assert response['meta']['cached'] is False
    assert response['pagination']['total_items'] == 2


@pytest.mark.asyncio
async def test_validation_runs_before_cache(client):
    client.get('/v2/researcher')
    response = client.get('/v2/researcher?sort_by=relevance')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_redis_unavailable_falls_back_to_database(
    client, researcher_factory
):
    unreachable = 'redis://127.0.0.1:1/0'
    app.dependency_overrides[get_search_cache] = lambda: SearchCache(
        redis_client=aioredis.from_url(
            unreachable, socket_connect_timeout=0.2, socket_timeout=0.2
        ),
        ttl=TTL,
    )
    SearchCache._unavailable_until = 0.0
    await researcher_factory()

    try:
        response = client.get('/v2/researcher')
        assert response.status_code == HTTPStatus.OK
        assert response.json()['meta']['cached'] is False
        # Backoff ativado: próximas requisições nem tentam o Redis
        assert SearchCache._unavailable_until > 0
    finally:
        SearchCache._unavailable_until = 0.0


def test_bump_generation_without_redis_does_not_raise():
    assert (
        bump_search_generation(f'redis://127.0.0.1:1/{uuid.uuid4().int % 16}')
        is None
    )


@pytest.mark.asyncio
async def test_real_dependency_wiring(client, redis_url, researcher_factory):
    settings = Settings(REDIS_URL=redis_url, REDIS_ENABLED=True)
    app.dependency_overrides.pop(get_search_cache)
    app.dependency_overrides[get_settings] = lambda: settings
    await researcher_factory()

    try:
        first = client.get('/v2/researcher').json()
        second = client.get('/v2/researcher').json()
    finally:
        # O pool global fica preso ao event loop deste TestClient
        redis_client._pool = None

    assert first['meta']['cached'] is False
    assert second['meta']['cached'] is True
