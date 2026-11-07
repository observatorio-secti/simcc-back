from fastapi import HTTPException
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

from simcc.core.logging.config import register_db_logging

async_engine = create_async_engine(ASYNC_URL, future=True)
register_db_logging(async_engine)

async_session = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

sync_engine = create_engine(SYNC_URL, future=True)
register_db_logging(sync_engine)

sync_session = sessionmaker(
    sync_engine,
    expire_on_commit=False,
    class_=Session,
)


if SETTINGS.ADMIN_DATABASE_URL:
    ADMIN_SYNC_URL = str(SETTINGS.ADMIN_DATABASE_URL).replace(
        '+asyncpg', '+psycopg'
    )
    ADMIN_ASYNC_URL = SETTINGS.ADMIN_DATABASE_URL

    admin_async_engine = create_async_engine(ADMIN_ASYNC_URL, future=True)
    register_db_logging(admin_async_engine)

    admin_async_session = async_sessionmaker(
        admin_async_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    admin_sync_engine = create_engine(ADMIN_SYNC_URL, future=True)
    register_db_logging(admin_sync_engine)

    admin_sync_session = sessionmaker(
        admin_sync_engine,
        expire_on_commit=False,
        class_=Session,
    )
else:
    ADMIN_SYNC_URL = None
    ADMIN_ASYNC_URL = None
    admin_async_engine = None
    admin_async_session = None
    admin_sync_engine = None
    admin_sync_session = None


async def get_async_session():
    async with async_session() as session:
        yield session


def get_sync_session():
    with sync_session() as session:
        yield session


async def get_admin_async_session():
    if admin_async_session is None:
        raise HTTPException(
            status_code=503,
            detail='ADMIN_DATABASE_URL não configurada no ambiente.',
        )
    async with admin_async_session() as session:
        yield session


def get_admin_sync_session():
    if admin_sync_session is None:
        raise RuntimeError('ADMIN_DATABASE_URL não configurada no ambiente.')
    with admin_sync_session() as session:
        yield session
