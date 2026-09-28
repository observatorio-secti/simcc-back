import pytest
from simcc.v1.ai.dependencies import get_ai_tracer
from simcc.v1.ai.telemetry.tracer import AITracer


@pytest.mark.asyncio
async def test_ai_tracer_initialization():
    tracer = AITracer()
    assert tracer.tracer is not None
    assert tracer.pipeline_span is not None
    assert tracer.request_id is not None
    assert tracer.query == ''

    # Test custom request context
    tracer.set_request_context(request_id='req-123', query='test query')
    assert tracer.request_id == 'req-123'
    assert tracer.query == 'test query'

    # Test trace stage
    async with tracer.trace_stage('test_stage'):
        pass

    assert 'test_stage' in tracer.stages
    assert tracer.stages['test_stage'] >= 0

    # Test finish
    tracer.set_meta('retrieved_count', 5)
    summary = tracer.finish(status='success')
    assert summary['status'] == 'success'
    assert summary['request_id'] == 'req-123'
    assert summary['query'] == 'test query'
    assert 'test_stage' in summary['stages']


def test_get_ai_tracer_dependency():
    tracer = get_ai_tracer()
    assert isinstance(tracer, AITracer)
    summary = tracer.finish(status='success')
    assert summary['status'] == 'success'
