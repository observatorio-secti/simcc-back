import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
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


class EnsurePathPrefixMiddleware:
    """Compatibilidade com proxies com ou sem strip do root_path.

    Quando a requisição externa chega já sem prefixo (ex: Nginx proxy_pass com
    barra no final), reconstrói o path para que Starlette case os mounts.
    """

    def __init__(self, app, prefix: str = ''):
        self.app = app
        self.prefix = prefix.rstrip('/')

    async def __call__(self, scope, receive, send):
        if scope['type'] in {'http', 'websocket'}:
            prefix = self.prefix
            if not prefix:
                for k, v in scope.get('headers', []):
                    if k.lower() == b'x-forwarded-prefix':
                        prefix = v.decode('latin1').strip().rstrip('/')
                        break
            if prefix:
                if not scope.get('root_path'):
                    scope['root_path'] = prefix
                path = scope.get('path', '')
                if not path.startswith(prefix):
                    new_path = f'{prefix}{path}'
                    scope['path'] = new_path
                    scope['raw_path'] = new_path.encode('latin1')
        await self.app(scope, receive, send)


app = FastAPI(
    title='SIMCC API',
    version='4.5.0',
    description='API do SIMCC',
    lifespan=lifespan,
    root_path=settings.ROOT_PATH,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(EnsurePathPrefixMiddleware, prefix=settings.ROOT_PATH)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
)
app.add_middleware(LoggingMiddleware)


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    v2_schema = v2_app.openapi()
    v1_schema = v1_app.openapi()

    merged_paths: dict[str, Any] = {}
    for path, item in v2_schema.get('paths', {}).items():
        merged_paths[f'/v2{path}'] = item
    for path, item in v1_schema.get('paths', {}).items():
        merged_paths[f'/v1{path}'] = item
        if path not in merged_paths:
            merged_paths[path] = item

    merged_components: dict[str, Any] = {}
    v1_components = v1_schema.get('components', {})
    v2_components = v2_schema.get('components', {})
    component_keys = set(v1_components.keys()) | set(v2_components.keys())
    for key in component_keys:
        merged_components[key] = {
            **v1_components.get(key, {}),
            **v2_components.get(key, {}),
        }

    merged_tags = []
    seen_tags = set()
    for tag in v2_schema.get('tags', []) + v1_schema.get('tags', []):
        tag_name = tag.get('name')
        if tag_name and tag_name not in seen_tags:
            seen_tags.add(tag_name)
            merged_tags.append(tag)

    openapi_schema: dict[str, Any] = {
        'openapi': '3.1.0',
        'info': {
            'title': app.title,
            'version': app.version,
            'description': app.description,
        },
        'paths': merged_paths,
        'components': merged_components,
    }
    if merged_tags:
        openapi_schema['tags'] = merged_tags
    if app.root_path:
        openapi_schema['servers'] = [{'url': app.root_path}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get('/docs', include_in_schema=False)
async def swagger_ui_html(req: Request) -> HTMLResponse:
    root_path = req.scope.get('root_path', '').rstrip('/')
    base = root_path if root_path else ''
    openapi_all = f'{base}/openapi.json' if base else '/openapi.json'
    openapi_v2 = f'{base}/v2/openapi.json' if base else '/v2/openapi.json'
    openapi_v1 = f'{base}/v1/openapi.json' if base else '/v1/openapi.json'

    return get_swagger_ui_html(
        openapi_url=openapi_all,
        title=f'{app.title} - Swagger UI',
        oauth2_redirect_url=(
            f'{base}/docs/oauth2-redirect' if base else '/docs/oauth2-redirect'
        ),
        swagger_ui_parameters={
            'urls': [
                {'name': 'SIMCC - Todas as rotas', 'url': openapi_all},
                {'name': 'SIMCC v2 (Atual)', 'url': openapi_v2},
                {'name': 'SIMCC v1', 'url': openapi_v1},
            ],
            'persistAuthorization': True,
        },
    )


@app.get('/redoc', include_in_schema=False)
async def redoc_html(req: Request) -> HTMLResponse:
    root_path = req.scope.get('root_path', '').rstrip('/')
    base = root_path if root_path else ''
    openapi_all = f'{base}/openapi.json' if base else '/openapi.json'
    return get_redoc_html(
        openapi_url=openapi_all,
        title=f'{app.title} - ReDoc',
    )


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
