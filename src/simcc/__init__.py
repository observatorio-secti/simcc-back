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
from simcc.routers import (
    external,
    graduate_program,
    institution,
    logs,
    maria,
    metrics,
    powerBi,
    research_group,
    researcher,
    routines,
)
from simcc.routers.production import (
    bibliographic,
    events,
    experience,
    intellectual_property,
    projects_guidance,
    summaries,
)

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        clean_old_logs()
    except Exception as e:
        sys.stderr.write(f'[Log Cleanup] Startup cleanup failed: {e}\n')
    yield


from simcc.core.telemetry import init_telemetry

app = FastAPI(lifespan=lifespan)
init_telemetry(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
)
app.add_middleware(LoggingMiddleware)


app.include_router(external.router)
app.include_router(bibliographic.router)
app.include_router(intellectual_property.router)
app.include_router(events.router)
app.include_router(projects_guidance.router)
app.include_router(summaries.router)
app.include_router(experience.router)
app.include_router(researcher.router)
app.include_router(metrics.router)
app.include_router(institution.router)
app.include_router(graduate_program.router)
app.include_router(research_group.router)
app.include_router(maria.router)
app.include_router(routines.router)
app.include_router(powerBi.router)
app.include_router(logs.router)


STATIC_DIR = Path(__file__).resolve().parent / 'static'
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    '/static',
    StaticFiles(directory=str(STATIC_DIR), html=True),
    name='static',
)

STORAGE_INSTITUTIONS_DIR = Path('storage/institutions').resolve()
STORAGE_INSTITUTIONS_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    '/storage/institutions',
    StaticFiles(directory=str(STORAGE_INSTITUTIONS_DIR)),
    name='institutions_storage',
)


@app.get('/', status_code=HTTPStatus.OK)
def read_root():
    return {'message': 'Olá Mundo!'}


@app.get('/favicon.ico', status_code=HTTPStatus.OK)
async def favicon():
    url = 'https://cdn-icons-png.flaticon.com/512/10446/10446694.png'
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    return StreamingResponse(iter([resp.content]), media_type='image/png')
