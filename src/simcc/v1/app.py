from fastapi import FastAPI

from simcc.v1.routers import (
    external,
    graduate_program,
    institution,
    logs,
    maria,
    metrics,
    powerBi,
    research_group,
    researcher,
)
from simcc.v1.routers.production import (
    bibliographic,
    events,
    experience,
    intellectual_property,
    projects_guidance,
    summaries,
)

v1_app = FastAPI()


v1_app.include_router(external.router)
v1_app.include_router(bibliographic.router)
v1_app.include_router(intellectual_property.router)
v1_app.include_router(events.router)
v1_app.include_router(projects_guidance.router)
v1_app.include_router(summaries.router)
v1_app.include_router(experience.router)
v1_app.include_router(researcher.router)
v1_app.include_router(metrics.router)
v1_app.include_router(institution.router)
v1_app.include_router(graduate_program.router)
v1_app.include_router(research_group.router)
v1_app.include_router(maria.router)
v1_app.include_router(powerBi.router)
v1_app.include_router(logs.router)
