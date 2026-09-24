from unittest.mock import AsyncMock, MagicMock

import pytest

from simcc.core.telemetry.config import TelemetryConfig
from simcc.core.telemetry.metrics import reset_metrics_for_tests
from simcc.core.telemetry.tracing import (
    get_in_memory_span_exporter,
    reset_tracing_for_tests,
    setup_tracing,
)
from simcc.v1.ai.telemetry.tracer import AITracer
from simcc.v1.services.maria_service import MariaService


@pytest.fixture(autouse=True)
def setup_in_memory():
    reset_tracing_for_tests()
    reset_metrics_for_tests()
    config = TelemetryConfig(
        enabled=True,
        exporter_type='in_memory',
        otlp_endpoint='http://localhost:4317',
        otlp_insecure=True,
        sampling_ratio=1.0,
        service_name='simcc-maria-test',
        service_namespace='simcc',
        service_version='1.0.0',
        environment='test',
    )
    setup_tracing(config)
    yield
    reset_tracing_for_tests()
    reset_metrics_for_tests()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maria_ask_chat_spans():
    exporter = get_in_memory_span_exporter()
    assert exporter is not None
    exporter.clear()

    tracer = AITracer(
        request_id='req_maria_test', query='Inteligência artificial na Bahia'
    )

    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value='Resposta sintetizada da MarIA')
    mock_embeddings = MagicMock()

    mock_cache = MagicMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock(return_value=True)

    mock_filters = MagicMock()
    mock_filters.model_dump.return_value = {'institutions': ['UFBA']}

    mock_planner = MagicMock()
    mock_planner.plan = AsyncMock(
        return_value=MagicMock(
            intent='researcher_search',
            semantic_query='Inteligência artificial',
            filters=mock_filters,
        )
    )

    mock_search = MagicMock()
    mock_search.search_researchers_hybrid = AsyncMock(return_value=[])
    mock_search.search_productions_hybrid = AsyncMock(return_value=[])

    service = MariaService(
        llm=mock_llm,
        embeddings=mock_embeddings,
        cache=mock_cache,
        tracer=tracer,
    )

    mock_session = AsyncMock()

    resp = await service.chat_ask(
        session=mock_session,
        query='Inteligência artificial na Bahia',
        planner=mock_planner,
        search_service=mock_search,
    )

    assert resp is not None
    spans = exporter.get_finished_spans()
    assert len(spans) >= 1

    span_names = [s.name for s in spans]
    assert 'ai.pipeline' in span_names
    assert 'ai.planner' in span_names
    assert 'ai.search' in span_names
