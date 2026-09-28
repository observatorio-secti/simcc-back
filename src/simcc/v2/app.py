from fastapi import FastAPI

from simcc.v2.routers import graduate_program, institution, researcher

v2_app = FastAPI()

v2_app.include_router(researcher.router)
v2_app.include_router(institution.router)
v2_app.include_router(graduate_program.router)
