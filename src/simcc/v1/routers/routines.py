from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header

from simcc.core.settings import Settings

router = APIRouter(tags=['Routines'])
SETTINGS = Settings()


@router.post(
    '/routines/researcher/{researcher_id}', status_code=HTTPStatus.ACCEPTED
)
async def trigger_researcher_routines(
    researcher_id: UUID,
    background_tasks: BackgroundTasks,
    x_internal_key: str | None = Header(default=None),
):
    # TODO
    return {'researcher_id': str(researcher_id)}
