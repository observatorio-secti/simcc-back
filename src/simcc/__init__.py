import sys
from contextlib import asynccontextmanager
from http import HTTPStatus
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from simcc.core.logging.cleanup import clean_old_logs
from simcc.core.logging.middleware import LoggingMiddleware
from simcc.core.settings import Settings
from simcc.v1 import v1_app
from simcc.v2 import v2_app

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        clean_old_logs()
    except Exception as e:
        sys.stderr.write(f'[Log Cleanup] Startup cleanup failed: {e}\n')
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
)
app.add_middleware(LoggingMiddleware)


v2_app.dependency_overrides = app.dependency_overrides
v1_app.dependency_overrides = app.dependency_overrides

STORAGE_INSTITUTIONS_DIR = Path('storage/institutions').resolve()
STORAGE_INSTITUTIONS_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    '/storage/institutions',
    StaticFiles(directory=str(STORAGE_INSTITUTIONS_DIR)),
    name='institutions_storage',
)

app.mount('/v2', v2_app)
app.mount('/v1', v1_app)
app.mount('/', v1_app)
