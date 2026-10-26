from fastapi import FastAPI

from simcc.v2.routers import (
    analytics,
    graduate_program,
    institution,
    production,
    researcher,
    suggestion,
)

v2_app = FastAPI(
    title='SIMCC API - v2',
    version='2.0.0',
    description='API do SIMCC versão 2',
)

v2_app.include_router(analytics.router)
v2_app.include_router(researcher.router)
v2_app.include_router(institution.router)
v2_app.include_router(graduate_program.router)
v2_app.include_router(production.router)
v2_app.include_router(suggestion.router)
