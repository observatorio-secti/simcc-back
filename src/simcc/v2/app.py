from fastapi import FastAPI

from simcc.v2.routers import researcher

v2_app = FastAPI()

v2_app.include_router(researcher.router)
