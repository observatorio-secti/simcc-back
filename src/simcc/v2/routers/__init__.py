from fastapi import APIRouter

from simcc.v2.routers.researcher import router as researcher_router

v2_router = APIRouter(prefix='/v2')
v2_router.include_router(researcher_router)

__all__ = ['v2_router']
