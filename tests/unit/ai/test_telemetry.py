import pytest

from simcc.v1.ai.telemetry.pricing import calculate_cost, estimate_tokens
from simcc.v1.ai.telemetry.tracer import AITracer


@pytest.mark.unit
def test_estimate_tokens():
    assert estimate_tokens('') == 0
    assert estimate_tokens('Olá mundo') >= 1
    assert estimate_tokens('Texto longo para teste de contagem de tokens') > 5


@pytest.mark.unit
def test_calculate_cost():
    cost = calculate_cost(
        'gpt-4o-mini', prompt_tokens=1000, completion_tokens=500
    )
    assert cost > 0.0
    assert isinstance(cost, float)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ai_tracer_lifecycle():
    tracer = AITracer(request_id='req_test_123', query='Pergunta de teste')
    tracer.set_meta('intent', 'researcher_search')

    async with tracer.trace_stage('planner'):
        pass

    async with tracer.trace_stage('search'):
        pass

    summary = tracer.finish(status='success')
    assert summary['request_id'] == 'req_test_123'
    assert summary['status'] == 'success'
    assert 'planner' in summary['stages']
    assert 'search' in summary['stages']
    assert summary['metadata']['intent'] == 'researcher_search'
