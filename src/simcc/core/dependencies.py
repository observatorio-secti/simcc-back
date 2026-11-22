from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlalchemy.orm import Session as _Session

from simcc.core.db.database import (
    get_async_session,
    get_sync_session,
)
from simcc.core.settings import get_settings
from simcc.v1.schemas import DefaultFilters

__all__ = ['AsyncSession', 'Filters', 'Session', 'get_settings']

AsyncSession = Annotated[_AsyncSession, Depends(get_async_session)]
Session = Annotated[_Session, Depends(get_sync_session)]

Filters = Annotated[DefaultFilters, Depends()]
