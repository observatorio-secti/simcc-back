from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.ai.dependencies import get_embeddings_provider
from simcc.core.db.database import get_async_session
from simcc.core.dependencies import get_settings
from simcc.core.settings import Settings
from simcc.v2.dependencies import researcher_query_params
from simcc.v2.schemas.envelope import ResponseEnvelope
from simcc.v2.schemas.researcher import ResearcherV2
from simcc.v2.services import researcher_service

router = APIRouter(tags=['v2 - Researchers'])


@router.get('/researcher', response_model=ResponseEnvelope[ResearcherV2])
async def search_researchers(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    params: Annotated[dict[str, Any], Depends(researcher_query_params)],
    embeddings_provider: Annotated[Any, Depends(get_embeddings_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ResponseEnvelope[ResearcherV2]:
    return await researcher_service.list_researchers(
        session=session,
        query_params=params,
        embeddings_provider=embeddings_provider,
        cosine_threshold=settings.AI_COSINE_DISTANCE_THRESHOLD,
    )
