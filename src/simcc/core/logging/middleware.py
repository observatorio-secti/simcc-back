import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from simcc.core.logging.context import (
    clear_logging_context,
    method_ctx,
    request_id_ctx,
    route_ctx,
    user_id_ctx,
)
from simcc.core.logging.events import (
    request_error,
    request_finished,
    request_received,
)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Clear/reset request context at the start of request handling
        clear_logging_context()

        # 1. Generate or extract request_id
        request_id = request.headers.get('x-request-id', str(uuid.uuid4()))

        # 2. Set context variables for the current async task
        token_request_id = request_id_ctx.set(request_id)
        token_route = route_ctx.set(request.url.path)
        token_method = method_ctx.set(request.method)

        start_time = time.perf_counter()

        # 3. Log request.received
        request_received(method=request.method, route=request.url.path)

        try:
            response = await call_next(request)

            # Check if user_id was set in request.state during request routing/auth
            user_id = getattr(request.state, 'user_id', None)
            if user_id:
                user_id_ctx.set(user_id)

            # 4. Measure duration
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # 5. Log request.finished
            request_finished(
                method=request.method,
                route=request.url.path,
                duration=duration_ms,
                user_id=user_id or user_id_ctx.get(),
            )

            try:
                record_http_duration(
                    method=request.method,
                    route=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
            except Exception:
                pass

            # Inject X-Request-ID to response headers
            response.headers['x-request-id'] = request_id
            return response

        except Exception as e:
            user_id = getattr(request.state, 'user_id', None)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # 6. Log request.error
            request_error(
                method=request.method,
                route=request.url.path,
                duration=duration_ms,
                error=str(e),
                user_id=user_id or user_id_ctx.get(),
            )
            raise e
        finally:
            # Reset contextvars to clean up the task execution scope
            request_id_ctx.reset(token_request_id)
            route_ctx.reset(token_route)
            method_ctx.reset(token_method)
