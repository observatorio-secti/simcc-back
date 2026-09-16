import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional
from uuid import uuid4

from opentelemetry.trace import StatusCode

from simcc.core.logging import logger
from simcc.core.telemetry.metrics import (
    record_ai_error,
    record_ai_request,
    record_ai_stage_duration,
)
from simcc.core.telemetry.tracing import get_tracer


class AITracer:
    def __init__(
        self, request_id: Optional[str] = None, query: Optional[str] = None
    ):
        self.request_id = request_id or str(uuid4())
        self.query = query or ''
        self.start_time = time.perf_counter()
        self.stages: Dict[str, float] = {}
        self.metadata: Dict[str, Any] = {
            'cache_hit': False,
            'intent': None,
            'retrieved_count': 0,
            'cutoff_dropped_count': 0,
            'final_count': 0,
            'model': 'gpt-4o-mini',
        }

        self.tracer = get_tracer('simcc.ai')
        self.pipeline_span = self.tracer.start_span('ai.pipeline')
        self.pipeline_span.set_attribute('ai.pipeline.name', 'maria_chat')
        self.pipeline_span.set_attribute('ai.model', 'gpt-4o-mini')
        self.pipeline_span.set_attribute('ai.query_length', len(self.query))
        self.pipeline_span.set_attribute('ai.request_id', self.request_id)

    def set_meta(self, key: str, value: Any) -> None:
        self.metadata[key] = value
        if key in {'intent', 'cache_hit', 'model'}:
            self.pipeline_span.set_attribute(f'ai.{key}', str(value))

    @asynccontextmanager
    async def trace_stage(self, stage_name: str) -> AsyncIterator[None]:
        t0 = time.perf_counter()
        stage_span = self.tracer.start_span(f'ai.{stage_name}')
        stage_span.set_attribute('ai.stage', stage_name)
        status = 'success'
        try:
            yield
        except Exception as exc:
            status = 'error'
            stage_span.record_exception(exc)
            stage_span.set_status(StatusCode.ERROR, str(exc))
            record_ai_error(stage_name, exc.__class__.__name__)
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self.stages[stage_name] = elapsed_ms
            stage_span.set_attribute('ai.stage_duration_ms', elapsed_ms)
            stage_span.end()
            record_ai_stage_duration(stage_name, status, elapsed_ms)

    def finish(
        self, status: str = 'success', error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        total_duration_ms = round(
            (time.perf_counter() - self.start_time) * 1000.0, 2
        )

        self.metadata['cache_hit'] = bool(
            self.metadata.get('cache_hit', False)
        )
        trace_summary = {
            'request_id': self.request_id,
            'query': self.query[:200] if self.query else '',
            'status': status,
            'total_duration_ms': total_duration_ms,
            'stages': self.stages,
            'metadata': self.metadata,
            'error_message': error_message,
        }

        try:
            span_ctx = self.pipeline_span.get_span_context()
            if span_ctx and span_ctx.is_valid:
                trace_summary['trace_id'] = f'{span_ctx.trace_id:032x}'
                trace_summary['span_id'] = f'{span_ctx.span_id:016x}'
        except Exception:
            pass

        self.pipeline_span.set_attribute(
            'ai.cache_hit', bool(self.metadata.get('cache_hit', False))
        )
        self.pipeline_span.set_attribute(
            'ai.intent', str(self.metadata.get('intent', ''))
        )
        self.pipeline_span.set_attribute(
            'ai.retrieval.documents_found',
            int(self.metadata.get('retrieved_count', 0)),
        )
        self.pipeline_span.set_attribute(
            'ai.retrieval.documents_after_cutoff',
            int(self.metadata.get('final_count', 0)),
        )
        self.pipeline_span.set_attribute(
            'ai.retrieval.dropped_count',
            int(self.metadata.get('cutoff_dropped_count', 0)),
        )
        self.pipeline_span.set_attribute(
            'ai.total_duration_ms', total_duration_ms
        )

        if status == 'success':
            self.pipeline_span.set_status(StatusCode.OK)
            cache_hit_flag = self.metadata.get('cache_hit')
            msg = (
                f'Pipeline de IA concluída em {total_duration_ms}ms '
                f'(cache_hit={cache_hit_flag})'
            )
            logger.info(
                'ai.pipeline.completed',
                message=msg,
                category='ai',
                request_id=self.request_id,
                duration=total_duration_ms,
                data=trace_summary,
            )
        else:
            self.pipeline_span.set_status(
                StatusCode.ERROR, error_message or 'Pipeline failed'
            )
            logger.error(
                'ai.pipeline.failed',
                message=f'Falha na pipeline de IA: {error_message}',
                category='ai',
                request_id=self.request_id,
                duration=total_duration_ms,
                data=trace_summary,
            )

        self.pipeline_span.end()
        record_ai_request(
            model=self.metadata.get('model', 'gpt-4o-mini'),
            intent=str(self.metadata.get('intent', 'unknown')),
            cache_hit=bool(self.metadata.get('cache_hit', False)),
            status=status,
        )

        return trace_summary
