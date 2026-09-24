import pytest

from simcc.core.telemetry.config import TelemetryConfig
from simcc.core.telemetry.metrics import reset_metrics_for_tests
from simcc.core.telemetry.tracing import (
    get_in_memory_span_exporter,
    reset_tracing_for_tests,
    setup_tracing,
)
from simcc.v1.ai.telemetry.tracer import AITracer


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
        service_name='simcc-ai-test',
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
async def test_ai_tracer_spans_lifecycle():
    exporter = get_in_memory_span_exporter()
    assert exporter is not None
    exporter.clear()

    tracer = AITracer(request_id='test-req-123', query='Pergunta de teste')
    tracer.set_meta('intent', 'researcher_search')
    tracer.set_meta('retrieved_count', 5)
    tracer.set_meta('cutoff_dropped_count', 1)
    tracer.set_meta('final_count', 4)

    async with tracer.trace_stage('planner'):
        pass

    async with tracer.trace_stage('cutoff'):
        pass

    summary = tracer.finish(status='success')
    assert summary['status'] == 'success'

    spans = exporter.get_finished_spans()
    assert len(spans) == 3

    span_names = [s.name for s in spans]
    assert 'ai.planner' in span_names
    assert 'ai.cutoff' in span_names
    assert 'ai.pipeline' in span_names

    pipeline_span = next(s for s in spans if s.name == 'ai.pipeline')
    assert pipeline_span.attributes['ai.intent'] == 'researcher_search'
    assert pipeline_span.attributes['ai.retrieval.documents_found'] == 5
    assert pipeline_span.attributes['ai.retrieval.dropped_count'] == 1
    assert pipeline_span.attributes['ai.retrieval.documents_after_cutoff'] == 4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ai_tracer_stage_error_span():
    exporter = get_in_memory_span_exporter()
    assert exporter is not None
    exporter.clear()

    tracer = AITracer(request_id='test-req-err', query='Erro')

    with pytest.raises(RuntimeError):
        async with tracer.trace_stage('synthesis'):
            raise RuntimeError('LLM timeout simulated')

    tracer.finish(status='failed', error_message='LLM timeout simulated')

    spans = exporter.get_finished_spans()
    assert len(spans) == 2

    synthesis_span = next(s for s in spans if s.name == 'ai.synthesis')
    assert synthesis_span.status.status_code.name == 'ERROR'

    pipeline_span = next(s for s in spans if s.name == 'ai.pipeline')
    assert pipeline_span.status.status_code.name == 'ERROR'
