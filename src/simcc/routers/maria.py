from enum import Enum

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from simcc.ai.dependencies import (
    get_ai_search_service,
    get_ai_tracer,
    get_cache_service,
    get_clarification_manager,
    get_embeddings_provider,
    get_llm_provider,
    get_query_planner,
)
from simcc.ai.schemas.maria import ChatRequest, ChatResponse, MariaResponse
from simcc.core.dependencies import AsyncSession
from simcc.services.maria_service import MariaService

router = APIRouter(tags=['MarIA - Inteligência Artificial'])


class SearchType(str, Enum):
    abstract = 'abstract'
    article = 'article'
    article_abstract = 'article_abstract'
    book = 'book'
    event = 'event'
    patent = 'patent'


def get_maria_service(
    llm=Depends(get_llm_provider),
    embeddings=Depends(get_embeddings_provider),
    cache=Depends(get_cache_service),
    tracer=Depends(get_ai_tracer),
    clarification_manager=Depends(get_clarification_manager),
):
    return MariaService(
        llm=llm,
        embeddings=embeddings,
        cache=cache,
        tracer=tracer,
        clarification_manager=clarification_manager,
    )


@router.get('/ai/researcher/summarize', response_model=MariaResponse)
async def summarize_researcher(
    session: AsyncSession,
    query: str = Query(
        ..., description='Termo ou pergunta para busca e resumo'
    ),
    search_type: SearchType = Query(
        SearchType.article, description='Onde buscar contexto'
    ),
    service: MariaService = Depends(get_maria_service),
):
    return await service.search_and_summarize(
        session, query, search_type.value
    )


@router.post('/ai/chat/ask', response_model=ChatResponse)
async def chat_ask(
    session: AsyncSession,
    request: ChatRequest,
    service: MariaService = Depends(get_maria_service),
    planner=Depends(get_query_planner),
    search_service=Depends(get_ai_search_service),
):
    """
    Interface de chat principal com a MarIA (resposta em lote/JSON).
    """
    return await service.chat_ask(
        session=session,
        query=request.query,
        planner=planner,
        search_service=search_service,
        session_id=request.session_id,
        clarification_response=request.clarification_response,
    )


@router.post('/ai/chat/ask/stream')
async def chat_ask_stream(
    session: AsyncSession,
    request: ChatRequest,
    service: MariaService = Depends(get_maria_service),
    planner=Depends(get_query_planner),
    search_service=Depends(get_ai_search_service),
):

    async def event_generator():
        async for event in service.chat_ask_stream(
            session=session,
            query=request.query,
            planner=planner,
            search_service=search_service,
            message_id=request.session_id,
            clarification_response=request.clarification_response,
        ):
            yield f'data: {event.model_dump_json()}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@router.get('/ai/production/classify')
async def classify_production():
    """
    Classifica uma produção científica usando IA.
    """
    # TODO: Implementar lógica de classificação no MariaService
    return {'message': 'Funcionalidade em desenvolvimento'}


@router.get('/ai/summary_search/', include_in_schema=False)
async def summary_search():
    return str()


@router.get(
    '/maria/researcher/{search_type}',
    include_in_schema=False,
)
async def legacy_researcher_search():
    return MariaResponse(query='', researchers=[])
