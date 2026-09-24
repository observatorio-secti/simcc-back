from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlalchemy.orm import Session as _Session

from simcc.core.db.database import (
    get_admin_async_session,
    get_admin_sync_session,
    get_async_session,
    get_sync_session,
)
from simcc.core.security import get_current_user
from simcc.core.settings import Settings
from simcc.v1.schemas import DefaultFilters


@lru_cache
def get_settings():
    return Settings()


AsyncSession = Annotated[_AsyncSession, Depends(get_async_session)]
Session = Annotated[_Session, Depends(get_sync_session)]

AdminAsyncSession = Annotated[_AsyncSession, Depends(get_admin_async_session)]
AdminSession = Annotated[_Session, Depends(get_admin_sync_session)]

CurrentUser = Annotated[dict, Depends(get_current_user)]

Filters = Annotated[DefaultFilters, Depends()]
