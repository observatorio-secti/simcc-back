"""Router para sugestão de termos de busca v2."""

from typing import Annotated

from fastapi import APIRouter, Depends

from simcc.core.dependencies import AsyncSession
from simcc.v2.dependencies import SearchCacheDep
from simcc.v2.schemas.query import as_query, forbid_unknown_params
from simcc.v2.schemas.suggestion import SuggestionParams, SuggestionResponse
from simcc.v2.services import suggestion_service

router = APIRouter(tags=['Suggestion v2'])


@router.get(
    '/suggestion',
    response_model=SuggestionResponse,
    dependencies=[Depends(forbid_unknown_params(SuggestionParams))],
)
async def list_suggestions(
    session: AsyncSession,
    cache: SearchCacheDep,
    params: Annotated[SuggestionParams, Depends(as_query(SuggestionParams))],
) -> SuggestionResponse:
    """Retorna termos do dicionário de pesquisa que começam com `q`."""
    return await suggestion_service.suggest_terms(
        session=session, params=params, cache=cache
    )
