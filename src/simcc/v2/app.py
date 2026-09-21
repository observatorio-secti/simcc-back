from fastapi import FastAPI

from simcc.v2.routers import researcher

v2_app = FastAPI(
    title='SIMCC API v2',
    description='SIMCC API Versão 2 - Sub-aplicação modular sem classes',
    version='2.0.0',
)

v2_app.include_router(researcher.router)
