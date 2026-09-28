from fastapi import FastAPI

from simcc.v3.routers import classifier_router

v3_app = FastAPI()


v3_app.include_router(classifier_router.router)
