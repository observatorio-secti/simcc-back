from http import HTTPStatus
from typing import Optional

import httpx
from fastapi import Request, Security
from fastapi.security import OAuth2PasswordBearer

from simcc.core.settings import Settings

SETTINGS = Settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/token', auto_error=False)


async def get_current_user(
    request: Request, token: Optional[str] = Security(oauth2_scheme)
):
    if not token:
        token = request.cookies.get('Authorization')
        if not token:
            return None
        token = token.replace('Bearer ', '', 1)
    async with httpx.AsyncClient() as client:
        response = await client.get(SETTINGS.ADMIN_URL)
        if response.status_code == HTTPStatus.OK:
            return response.json()
