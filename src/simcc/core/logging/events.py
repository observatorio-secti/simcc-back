import logging
from typing import Any, Optional

import structlog

logger = structlog.get_logger()
from simcc.core.logging.constants import LogCategory, LogEvent


def request_received(
    method: str, route: str, user_id: Any = None, **kwargs
) -> None:
    message = f'Request received: {method} {route}'
    logger.info(
        LogEvent.HTTP_RECEIVED,
        message=message,
        category=LogCategory.HTTP,
        method=method,
        route=route,
        user_id=user_id,
        **kwargs,
    )


def request_finished(
    method: str,
    route: str,
    duration: float,
    user_id: Any = None,
    status_code: Optional[int] = None,
    **kwargs,
) -> None:
    message = f'Request finished: {method} {route}'
    if status_code is not None:
        message += f' [{status_code}]'

    # Se status for 4xx tratamos como warning, 5xx como error, demais como info
    if status_code and status_code >= 500:
        log_func = logger.error
    elif status_code and status_code >= 400:
        log_func = logger.warning
    else:
        log_func = logger.info

    log_func(
        LogEvent.HTTP_FINISHED,
        message=message,
        category=LogCategory.HTTP,
        method=method,
        route=route,
        duration=duration,
        user_id=user_id,
        status_code=status_code,
        **kwargs,
    )


def request_error(
    method: str,
    route: str,
    duration: float,
    error: str,
    user_id: Any = None,
    status_code: Optional[int] = 500,
    **kwargs,
) -> None:
    message = f'Request error: {method} {route} - {error}'
    if status_code is not None:
        message += f' [{status_code}]'

    logger.error(
        LogEvent.HTTP_ERROR,
        message=message,
        category=LogCategory.HTTP,
        method=method,
        route=route,
        duration=duration,
        error_message=error,
        user_id=user_id,
        status_code=status_code,
        **kwargs,
    )


def routine_started(routine_name: str, **kwargs) -> None:
    message = f'Routine started: {routine_name}'
    logger.info(
        LogEvent.ROUTINE_STARTED,
        message=message,
        category=LogCategory.ROUTINE,
        routine_name=routine_name,
        **kwargs,
    )


def routine_finished(routine_name: str, duration: float, **kwargs) -> None:
    message = f'Routine finished: {routine_name}'
    logger.info(
        LogEvent.ROUTINE_FINISHED,
        message=message,
        category=LogCategory.ROUTINE,
        routine_name=routine_name,
        duration=duration,
        **kwargs,
    )


def routine_error(
    routine_name: str, duration: float, error: str, **kwargs
) -> None:
    message = f'Routine error: {routine_name} - {error}'
    logger.error(
        LogEvent.ROUTINE_ERROR,
        message=message,
        category=LogCategory.ROUTINE,
        routine_name=routine_name,
        duration=duration,
        error_message=error,
        **kwargs,
    )


def routine_step_started(step_name: str, **kwargs) -> None:
    message = f'Routine step started: {step_name}'
    logger.info(
        LogEvent.ROUTINE_STEP_STARTED,
        message=message,
        category=LogCategory.ROUTINE,
        step_name=step_name,
        **kwargs,
    )


def routine_step_finished(
    step_name: str, duration: Optional[float] = None, **kwargs
) -> None:
    message = f'Routine step finished: {step_name}'
    logger.info(
        LogEvent.ROUTINE_STEP_FINISHED,
        message=message,
        category=LogCategory.ROUTINE,
        step_name=step_name,
        duration=duration,
        **kwargs,
    )


def routine_progress(
    step_name: str,
    current: int,
    total: int,
    succeeded: int,
    failed: int,
    **kwargs,
) -> None:
    message = f'Routine progress [{current}/{total}]: {step_name}'
    logger.info(
        LogEvent.ROUTINE_PROGRESS,
        message=message,
        category=LogCategory.ROUTINE,
        step_name=step_name,
        current=current,
        total=total,
        succeeded=succeeded,
        failed=failed,
        **kwargs,
    )


def routine_item_error(item_id: str, error: str, **kwargs) -> None:
    message = f'Routine item error ({item_id}): {error}'
    logger.warning(
        LogEvent.ROUTINE_ITEM_ERROR,
        message=message,
        category=LogCategory.ROUTINE,
        item_id=str(item_id),
        error_message=error,
        **kwargs,
    )


def script_started(script_name: str, **kwargs) -> None:
    message = f'Script started: {script_name}'
    logger.info(
        LogEvent.SCRIPT_STARTED,
        message=message,
        category=LogCategory.SCRIPT,
        script_name=script_name,
        **kwargs,
    )


def script_finished(script_name: str, duration: float, **kwargs) -> None:
    message = f'Script finished: {script_name}'
    logger.info(
        LogEvent.SCRIPT_FINISHED,
        message=message,
        category=LogCategory.SCRIPT,
        script_name=script_name,
        duration=duration,
        **kwargs,
    )


def script_error(
    script_name: str, duration: float, error: str, **kwargs
) -> None:
    message = f'Script error: {script_name} - {error}'
    logger.error(
        LogEvent.SCRIPT_ERROR,
        message=message,
        category=LogCategory.SCRIPT,
        script_name=script_name,
        duration=duration,
        error_message=error,
        **kwargs,
    )


def script_step_started(step_name: str, **kwargs) -> None:
    message = f'Script step started: {step_name}'
    logger.info(
        LogEvent.SCRIPT_STEP_STARTED,
        message=message,
        category=LogCategory.SCRIPT,
        step_name=step_name,
        **kwargs,
    )


def script_step_finished(
    step_name: str, duration: Optional[float] = None, **kwargs
) -> None:
    message = f'Script step finished: {step_name}'
    logger.info(
        LogEvent.SCRIPT_STEP_FINISHED,
        message=message,
        category=LogCategory.SCRIPT,
        step_name=step_name,
        duration=duration,
        **kwargs,
    )


def script_progress(
    step_name: str,
    current: int,
    total: int,
    succeeded: int,
    failed: int,
    **kwargs,
) -> None:
    message = f'Script progress [{current}/{total}]: {step_name}'
    logger.info(
        LogEvent.SCRIPT_PROGRESS,
        message=message,
        category=LogCategory.SCRIPT,
        step_name=step_name,
        current=current,
        total=total,
        succeeded=succeeded,
        failed=failed,
        **kwargs,
    )


def script_item_error(item_id: str, error: str, **kwargs) -> None:
    message = f'Script item error ({item_id}): {error}'
    logger.warning(
        LogEvent.SCRIPT_ITEM_ERROR,
        message=message,
        category=LogCategory.SCRIPT,
        item_id=str(item_id),
        error_message=error,
        **kwargs,
    )


def query_error(
    operation_name: str,
    database_name: str,
    error: str,
    duration: Optional[float] = None,
    sql: Optional[str] = None,
    **kwargs,
) -> None:

    message = (
        f'Database query error in operation: {operation_name} '
        f'on db: {database_name}'
    )

    # We never log SQL in production, only if LOG_LEVEL is DEBUG
    from simcc.core.logging.config import get_configured_log_level

    log_data = {
        'operation_name': operation_name,
        'database_name': database_name,
        'error_message': error,
    }

    if get_configured_log_level() <= logging.DEBUG and sql:
        log_data['sql'] = sql

    logger.error(
        LogEvent.DB_ERROR,
        message=message,
        category=LogCategory.DATABASE,
        duration=duration,
        data=log_data,
        **kwargs,
    )


def query_slow(
    operation_name: str,
    database_name: str,
    duration: float,
    sql: Optional[str] = None,
    **kwargs,
) -> None:
    message = (
        f'Database slow query in operation: {operation_name} '
        f'on db: {database_name} ({duration:.2f}ms)'
    )

    from simcc.core.logging.config import get_configured_log_level

    log_data = {
        'operation_name': operation_name,
        'database_name': database_name,
        'duration': duration,
    }

    if get_configured_log_level() <= logging.DEBUG and sql:
        log_data['sql'] = sql

    logger.warning(
        LogEvent.DB_SLOW_QUERY,
        message=message,
        category=LogCategory.DATABASE,
        duration=duration,
        data=log_data,
        **kwargs,
    )
