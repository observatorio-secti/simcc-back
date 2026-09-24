from fastapi import Depends

from simcc.core.cache import CacheService, get_redis_client
from simcc.core.dependencies import get_settings
from simcc.v1.ai.clarification import ClarificationManager
from simcc.v1.ai.providers.openai_provider import OpenAIProvider
from simcc.v1.ai.query_planner import QueryPlanner
from simcc.v1.ai.telemetry.tracer import AITracer
from simcc.v1.services.ai_search_service import AISearchService
from simcc.v1.services.researcher_matcher import ResearcherMatcher


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


def get_researcher_matcher() -> ResearcherMatcher:
    return ResearcherMatcher()


def get_clarification_manager(
    matcher: ResearcherMatcher = Depends(get_researcher_matcher),
    cache: CacheService = Depends(get_cache_service),
) -> ClarificationManager:
    return ClarificationManager(matcher=matcher, cache=cache)


def get_ai_metrics_service():
    from simcc.v1.services.ai_metrics_service import AIMetricsService

    return AIMetricsService()
