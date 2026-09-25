import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from simcc import app
from simcc.core.db.database import get_async_session
from simcc.core.db.models import table_registry
from simcc.v2.dependencies import get_search_cache
from simcc.v2.services.search_cache import SearchCache
from tests.setup_mvs import drop_test_mvs, init_test_mvs

pytest_plugins = [
    'tests.fixtures.graduate_program',
    'tests.fixtures.institution',
    'tests.fixtures.location',
    'tests.fixtures.researcher',
    'tests.fixtures.search',
]


@pytest.fixture
def client(session, cache):
    def get_session_override():
        return session

    def get_search_cache_override():
        return cache

    with TestClient(app) as client:
        app.dependency_overrides[get_async_session] = get_session_override
        app.dependency_overrides[get_search_cache] = get_search_cache_override
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope='session')
def engine():
    pg_version = 'pgvector/pgvector:pg17'
    with PostgresContainer(pg_version, driver='psycopg') as postgres:
        _engine = create_async_engine(postgres.get_connection_url())
        yield _engine


@pytest.fixture(scope='session')
def redis_container():
    with RedisContainer('redis:7-alpine') as container:
        yield container


@pytest.fixture
def redis_url(redis_container):
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    url = f'redis://{host}:{port}/0'
    client = redis_container.get_client()
    client.flushdb()
    yield url
    client.flushdb()


@pytest.fixture
def cache(redis_url):
    # As conexões são abertas sob demanda, já no event loop do app
    SearchCache._unavailable_until = 0.0
    return SearchCache(
        redis_client=aioredis.from_url(redis_url, decode_responses=True),
        ttl=60,
    )


@pytest_asyncio.fixture(scope='session', autouse=True)
async def setup_database(engine):
    async with engine.begin() as conn:
        # TODO: Remover esse create extension daqui
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))

        await conn.run_sync(table_registry.metadata.create_all)
        await init_test_mvs(conn)
    yield
    async with engine.begin() as conn:
        await drop_test_mvs(conn)
        await conn.run_sync(table_registry.metadata.drop_all)


@pytest_asyncio.fixture
async def session(engine):
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode='create_savepoint',
        ) as session:
            yield session
        # Rollback explícito: sair de `connection.begin()` faria commit
        # e vazaria os dados deste teste para os seguintes.
        await transaction.rollback()
