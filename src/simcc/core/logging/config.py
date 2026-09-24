import logging
from datetime import datetime
from typing import Any

import structlog
from opentelemetry import trace as otel_trace

from simcc.core.logging.context import get_logging_context
from simcc.core.logging.handlers import dispatch_log

LEVEL_MAP = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'warn': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'fatal': logging.CRITICAL,
}


def get_configured_log_level() -> int:
    try:
        from simcc.core.settings import Settings

        settings = Settings()
        lvl_str = getattr(settings, 'LOG_LEVEL', 'INFO').lower()
        return LEVEL_MAP.get(lvl_str, logging.INFO)
    except Exception:
        return logging.INFO


def level_filter_processor(logger, method_name, event_dict):
    configured_level = get_configured_log_level()
    current_level = LEVEL_MAP.get(method_name.lower(), logging.INFO)
    if current_level < configured_level:
        raise structlog.DropEvent
    return event_dict


def format_schema_processor(logger, method_name, event_dict):
    ctx = get_logging_context()

    # Convert all enums in event_dict to their string values
    from enum import Enum

    for k, v in list(event_dict.items()):
        if isinstance(v, Enum):
            event_dict[k] = v.value

    # 1. Level
    level = event_dict.pop('level', method_name)
    if isinstance(level, Enum):
        level = level.value
    level = str(level).lower()

    # 2. Timestamp
    timestamp = event_dict.pop('timestamp', None)
    if not timestamp:
        timestamp = datetime.utcnow().isoformat() + 'Z'

    # 3. Application
    application = event_dict.pop(
        'application', ctx.get('application') or 'simcc'
    )
    if isinstance(application, Enum):
        application = application.value

    # 4. Category
    category = event_dict.pop('category', 'system')
    if isinstance(category, Enum):
        category = category.value

    # 5. Event and Message
    event_val = event_dict.pop('event', None)
    if isinstance(event_val, Enum):
        event_val = event_val.value

    message_val = event_dict.pop('message', None)
    if isinstance(message_val, Enum):
        message_val = message_val.value

    if event_val and not message_val:
        if isinstance(event_val, str) and '.' in event_val:
            event = event_val
            message = ''
        else:
            event = 'system.log'
            message = str(event_val)
    elif event_val and message_val:
        event = str(event_val)
        message = str(message_val)
    elif not event_val and message_val:
        event = 'system.log'
        message = str(message_val)
    else:
        event = 'system.log'
        message = ''

    # 6. Request ID
    request_id = event_dict.pop('request_id', ctx.get('request_id'))

    # 7. Duration
    duration = event_dict.pop('duration', None)
    if duration is not None:
        try:
            duration = float(duration)
        except ValueError:
            pass

    # 8. Environment and Hostname (standard root-level fields)
    environment = event_dict.pop(
        'environment', ctx.get('environment') or 'development'
    )
    hostname = event_dict.pop('hostname', ctx.get('hostname'))

    # 9. Data: standardized by category
    if category == 'http':
        data_dict = {
            'route': ctx.get('route'),
            'method': ctx.get('method'),
            'user_id': ctx.get('user_id'),
            'error_message': None,
        }
    elif category == 'database':
        data_dict = {
            'database_name': None,
            'operation_name': None,
            'error_message': None,
            'sql': None,
        }
    elif category == 'routine':
        data_dict = {
            'routine_name': ctx.get('routine_name'),
            'error_message': None,
            'items_found': None,
            'items_succeeded': None,
            'items_failed': None,
        }
    elif category == 'script':
        data_dict = {
            'script_name': ctx.get('script_name'),
            'error_message': None,
            'items_found': None,
            'items_succeeded': None,
            'items_failed': None,
        }
    else:
        # 'system', 'frontend' or other categories
        data_dict = {}
        for key in [
            'route',
            'method',
            'user_id',
            'routine_name',
            'script_name',
        ]:
            val = ctx.get(key)
            if val is not None:
                data_dict[key] = val

    # Merge custom 'data' dictionary if passed
    user_data = event_dict.pop('data', {})
    if isinstance(user_data, dict):
        data_dict.update(user_data)

    # Merge remaining dynamic extra keys
    for k, v in event_dict.items():
        data_dict[k] = v

    # Correlate OpenTelemetry trace_id and span_id if available
    try:
        current_span = otel_trace.get_current_span()
        if current_span and current_span.get_span_context().is_valid:
            span_ctx = current_span.get_span_context()
            data_dict.setdefault('trace_id', f'{span_ctx.trace_id:032x}')
            data_dict.setdefault('span_id', f'{span_ctx.span_id:016x}')
    except Exception:
        pass

    formatted_log = {
        'timestamp': timestamp,
        'level': level,
        'application': application,
        'environment': environment,
        'hostname': hostname,
        'category': category,
        'event': event,
        'message': message,
        'request_id': request_id,
        'duration': duration,
        'data': data_dict,
    }

    return formatted_log


class CustomLogger:
    def msg(self, *args, **kwargs):
        if args and isinstance(args[0], dict):
            dispatch_log(args[0])
        elif kwargs:
            dispatch_log(kwargs)

    log = msg
    debug = msg
    info = msg
    warn = msg
    warning = msg
    error = msg
    critical = msg
    fatal = msg


def configure_logging():
    structlog.configure(
        processors=[
            level_filter_processor,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt='iso'),
            format_schema_processor,
        ],
        logger_factory=lambda: CustomLogger(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )


import inspect
import time

from sqlalchemy import event

from simcc.core.logging.events import query_error


def get_logical_operation_name() -> str:
    try:
        stack = inspect.stack()
        for frame_info in stack:
            module_name = frame_info.frame.f_globals.get('__name__', '')
            if any(
                p in module_name
                for p in [
                    'simcc.repositories',
                    'simcc.queries',
                    'scripts',
                    'simcc.v1.services',
                ]
            ):
                func_name = frame_info.function
                self_obj = frame_info.frame.f_locals.get('self', None)
                if self_obj:
                    class_name = self_obj.__class__.__name__
                    return f'{class_name}.{func_name}'
                module_short = module_name.split('.')[-1]
                return f'{module_short}.{func_name}'
    except Exception:
        pass
    return 'database.query'


def register_db_logging(engine: Any) -> None:
    # Handle AsyncEngine by registering listeners on the underlying sync_engine
    target_engine = getattr(engine, 'sync_engine', engine)

    # Avoid duplicate registrations on the same engine
    if getattr(target_engine, '_db_logging_registered', False):
        return

    @event.listens_for(target_engine, 'before_cursor_execute')
    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        if context:
            context._query_start_time = time.perf_counter()

    @event.listens_for(target_engine, 'handle_error')
    def handle_exception(exception_context):
        duration = None
        exec_ctx = exception_context.execution_context
        if exec_ctx and hasattr(exec_ctx, '_query_start_time'):
            duration = (
                time.perf_counter() - exec_ctx._query_start_time
            ) * 1000.0

        sql = exception_context.statement
        engine_obj = exception_context.engine
        db_name = (
            engine_obj.url.database
            if engine_obj and engine_obj.url
            else 'unknown'
        )

        operation_name = get_logical_operation_name()

        query_error(
            operation_name=operation_name,
            database_name=db_name or 'unknown',
            error=str(exception_context.original_exception),
            duration=duration,
            sql=sql,
        )

    target_engine._db_logging_registered = True
