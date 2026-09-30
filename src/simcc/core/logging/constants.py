from enum import Enum


class LogCategory(str, Enum):
    HTTP = 'http'
    DATABASE = 'database'
    ROUTINE = 'routine'
    SCRIPT = 'script'
    FRONTEND = 'frontend'
    SYSTEM = 'system'


class LogEvent(str, Enum):
    HTTP_RECEIVED = 'request.received'
    HTTP_FINISHED = 'request.finished'
    HTTP_ERROR = 'request.error'

    DB_ERROR = 'query.error'
    DB_SLOW_QUERY = 'query.slow'

    ROUTINE_STARTED = 'routine.started'
    ROUTINE_FINISHED = 'routine.finished'
    ROUTINE_ERROR = 'routine.error'
    ROUTINE_STEP_STARTED = 'routine.step.started'
    ROUTINE_STEP_FINISHED = 'routine.step.finished'
    ROUTINE_PROGRESS = 'routine.progress'
    ROUTINE_ITEM_ERROR = 'routine.item_error'

    SCRIPT_STARTED = 'script.started'
    SCRIPT_FINISHED = 'script.finished'
    SCRIPT_ERROR = 'script.error'
    SCRIPT_STEP_STARTED = 'script.step.started'
    SCRIPT_STEP_FINISHED = 'script.step.finished'
    SCRIPT_PROGRESS = 'script.progress'
    SCRIPT_ITEM_ERROR = 'script.item_error'


# Limiar padrão em milissegundos para classificação de queries lentas
SLOW_QUERY_THRESHOLD_MS: float = 1000.0
