from fastapi import Depends

from simcc.ai.providers.openai_provider import OpenAIProvider
from simcc.ai.query_planner import QueryPlanner
from simcc.ai.telemetry.tracer import AITracer
from simcc.core.cache import CacheService, get_redis_client
from simcc.core.dependencies import get_settings
from simcc.services.ai_search_service import AISearchService


def get_llm_provider(settings=Depends(get_settings)):
    return OpenAIProvider(api_key=settings.OPENAI_API_KEY)


def get_embeddings_provider(settings=Depends(get_settings)):
    return OpenAIProvider(api_key=settings.OPENAI_API_KEY)


def get_query_planner(settings=Depends(get_settings)):

    return QueryPlanner(api_key=settings.OPENAI_API_KEY)


def get_cache_service(settings=Depends(get_settings)) -> CacheService:
    if not settings.REDIS_ENABLED:
        return CacheService(redis_client=None, enabled=False)

    redis_client = get_redis_client(settings.REDIS_URL)
    return CacheService(
        redis_client=redis_client,
        enabled=settings.REDIS_ENABLED,
        default_ttl=settings.AI_CACHE_TTL,
    )


def get_ai_tracer() -> AITracer:
    return AITracer()


def get_ai_search_service(
    embeddings_provider=Depends(get_embeddings_provider),
    settings=Depends(get_settings),
):
    return AISearchService(
        embeddings_provider=embeddings_provider,
        cosine_distance_threshold=settings.AI_COSINE_DISTANCE_THRESHOLD,
    )
