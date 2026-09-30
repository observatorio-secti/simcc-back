import pytest
import structlog
from datetime import datetime

from simcc.core.logging.config import format_schema_processor, level_filter_processor
from simcc.core.logging.constants import LogCategory, LogEvent
from simcc.core.logging.context import (
    clear_logging_context,
    request_id_ctx,
    route_ctx,
    method_ctx,
    user_id_ctx,
)


def test_format_schema_processor_default_fields():
    clear_logging_context()
    event_dict = {
        'level': 'info',
        'event': 'test.event',
        'message': 'Mensagem de teste',
    }
    result = format_schema_processor(None, 'info', event_dict)

    assert result['level'] == 'info'
    assert result['application'] == 'simcc'
    assert result['environment'] in ['development', 'test', 'production']
    assert result['event'] == 'test.event'
    assert result['message'] == 'Mensagem de teste'
    assert 'timestamp' in result
    assert isinstance(result['data'], dict)


def test_format_schema_processor_context_propagation():
    clear_logging_context()
    request_id_ctx.set('req-test-123')
    route_ctx.set('/v1/test')
    method_ctx.set('POST')
    user_id_ctx.set('user-456')

    event_dict = {
        'category': LogCategory.HTTP,
        'event': LogEvent.HTTP_FINISHED,
        'duration': 15.5,
    }
    result = format_schema_processor(None, 'info', event_dict)

    assert result['request_id'] == 'req-test-123'
    assert result['category'] == 'http'
    assert result['duration'] == 15.5
    assert result['data']['route'] == '/v1/test'
    assert result['data']['method'] == 'POST'
    assert result['data']['user_id'] == 'user-456'

    clear_logging_context()


def test_format_schema_processor_categories():
    clear_logging_context()

    # Test database category schema
    db_event = {
        'category': LogCategory.DATABASE,
        'event': LogEvent.DB_ERROR,
        'data': {
            'database_name': 'simcc_db',
            'operation_name': 'ResearcherRepo.get_by_id',
            'error_message': 'Connection timeout',
        },
    }
    db_result = format_schema_processor(None, 'error', db_event)
    assert db_result['category'] == 'database'
    assert db_result['data']['database_name'] == 'simcc_db'
    assert db_result['data']['operation_name'] == 'ResearcherRepo.get_by_id'
    assert db_result['data']['error_message'] == 'Connection timeout'

    # Test routine category schema
    routine_event = {
        'category': LogCategory.ROUTINE,
        'event': LogEvent.ROUTINE_FINISHED,
        'data': {
            'routine_name': 'sync_lattes',
            'items_found': 100,
            'items_succeeded': 98,
            'items_failed': 2,
        },
    }
    routine_result = format_schema_processor(None, 'info', routine_event)
    assert routine_result['category'] == 'routine'
    assert routine_result['data']['routine_name'] == 'sync_lattes'
    assert routine_result['data']['items_found'] == 100
    assert routine_result['data']['items_succeeded'] == 98
    assert routine_result['data']['items_failed'] == 2


def test_level_filter_processor(monkeypatch):
    # Simular LOG_LEVEL = WARNING via variável de ambiente
    monkeypatch.setenv('LOG_LEVEL', 'WARNING')

    # Evento INFO deve ser descartado
    with pytest.raises(structlog.DropEvent):
        level_filter_processor(None, 'info', {'event': 'should.be.dropped'})

    # Evento WARNING ou ERROR deve passar
    res_warn = level_filter_processor(None, 'warning', {'event': 'warning.pass'})
    assert res_warn['event'] == 'warning.pass'

    res_err = level_filter_processor(None, 'error', {'event': 'error.pass'})
    assert res_err['event'] == 'error.pass'


def test_format_schema_processor_http_status_code():
    clear_logging_context()
    event_dict = {
        'category': LogCategory.HTTP,
        'event': LogEvent.HTTP_FINISHED,
        'data': {
            'route': '/v1/researchers',
            'method': 'GET',
            'status_code': 200,
            'user_id': None,
        },
    }
    result = format_schema_processor(None, 'info', event_dict)
    assert result['data']['status_code'] == 200
    assert result['data']['route'] == '/v1/researchers'


def test_query_slow_event():
    from simcc.core.logging.events import query_slow
    from simcc.core.logging.handlers import LOG_DESTINATIONS

    captured = []
    def mock_dest(log):
        captured.append(log)

    LOG_DESTINATIONS.append(mock_dest)
    try:
        query_slow(
            operation_name='ResearcherQuery.get_all',
            database_name='simcc_prod',
            duration=1250.5,
            sql='SELECT * FROM researchers',
        )

        assert len(captured) == 1
        log = captured[0]
        assert log['event'] == LogEvent.DB_SLOW_QUERY
        assert log['category'] == LogCategory.DATABASE
        assert log['level'] == 'warning'
        assert log['duration'] == 1250.5
        assert log['data']['operation_name'] == 'ResearcherQuery.get_all'
        assert log['data']['database_name'] == 'simcc_prod'
    finally:
        LOG_DESTINATIONS.remove(mock_dest)
