from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)

from simcc.core.settings import Settings

SETTINGS = Settings()

SYNC_URL = str(SETTINGS.DATABASE_URL).replace('+asyncpg', '+psycopg')
ASYNC_URL = SETTINGS.DATABASE_URL

async_engine = create_async_engine(ASYNC_URL, future=True)

async_session = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

sync_engine = create_engine(SYNC_URL, future=True)

sync_session = sessionmaker(
    sync_engine,
    expire_on_commit=False,
    class_=Session,
)


async def get_async_session():
    async with async_session() as session:
        yield session


def get_sync_session():
    with sync_session() as session:
        yield session
