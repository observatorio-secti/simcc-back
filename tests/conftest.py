import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from simcc import app
from simcc.core.db.database import get_async_session
from simcc.core.db.models import table_registry
from tests.setup_mvs import drop_test_mvs, init_test_mvs

pytest_plugins = [
    'tests.fixtures.graduate_program',
    'tests.fixtures.institution',
    'tests.fixtures.researcher',
]


@pytest.fixture
def client(session):
    def get_session_override():
        return session

    with TestClient(app) as client:
        app.dependency_overrides[get_async_session] = get_session_override
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope='session')
def engine():
    pg_version = 'pgvector/pgvector:pg17'
    with PostgresContainer(pg_version, driver='psycopg') as postgres:
        _engine = create_async_engine(postgres.get_connection_url())
        yield _engine


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
        async with connection.begin():
            async with AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode='create_savepoint',
            ) as session:
                yield session
