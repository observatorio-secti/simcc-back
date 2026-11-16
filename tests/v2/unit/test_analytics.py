# ruff: noqa: PLR2004, PLR0913, PLR0917
"""Testes unitários para o endpoint de métricas do GA4 v2."""

import re
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from google.analytics.data_v1beta.types import (
    DimensionValue,
    Filter,
    MetricValue,
    Row,
    RunReportResponse,
)

from simcc import app
from simcc.core.dependencies import get_settings
from simcc.core.settings import Settings


@pytest.fixture(scope='session', autouse=True)
def setup_database():
    """Sobrescreve fixture global para testes sem banco/docker."""
    return


def _create_mock_row(
    date: str,
    event_name: str,
    country: str,
    host_name: str,
    event_count: str,
    active_users: str,
):
    dim_mocks = [
        MagicMock(value=v) for v in (date, event_name, country, host_name)
    ]
    met_mocks = [MagicMock(value=v) for v in (event_count, active_users)]

    row_mock = MagicMock()
    row_mock.dimension_values = dim_mocks
    row_mock.metric_values = met_mocks
    return row_mock


def test_analytics_missing_property_id():
    """Retorna 500 se GA4_PROPERTY_ID não estiver configurado."""
    mock_settings = Settings(GA4_PROPERTY_ID=None)

    app.dependency_overrides[get_settings] = lambda: mock_settings
    try:
        with TestClient(app) as test_client:
            response = test_client.get('/v2/analytics')
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
            assert 'GA4_PROPERTY_ID' in response.json()['detail']
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_analytics_unknown_params():
    """Retorna 422 caso query params desconhecidos sejam enviados."""
    mock_settings = Settings(GA4_PROPERTY_ID='123456789')

    app.dependency_overrides[get_settings] = lambda: mock_settings
    try:
        with TestClient(app) as test_client:
            response = test_client.get('/v2/analytics?param_invalido=teste')
            assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    finally:
        app.dependency_overrides.pop(get_settings, None)


@patch('simcc.v2.routers.analytics.BetaAnalyticsDataClient')
def test_analytics_success(mock_client_cls):
    """Retorna 200 e dados normalizados quando o GA4 responde com sucesso."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.rows = [
        _create_mock_row(
            date='20241010',
            event_name='page_view',
            country='Brazil',
            host_name='simcc.uesc.br',
            event_count='150',
            active_users='80',
        ),
        _create_mock_row(
            date='20241011',
            event_name='click',
            country='Brazil',
            host_name='simcc.uesc.br',
            event_count='45',
            active_users='20',
        ),
    ]
    mock_client.run_report.return_value = mock_response

    mock_settings = Settings(
        GA4_PROPERTY_ID='123456789',
        GA4_SITE_URL='simcc.uesc.br',
    )

    app.dependency_overrides[get_settings] = lambda: mock_settings
    try:
        with TestClient(app) as test_client:
            response = test_client.get(
                '/v2/analytics?start_date=30daysAgo&end_date=today'
            )
            assert response.status_code == HTTPStatus.OK
            body = response.json()

            assert 'data' in body
            assert 'summary' in body
            assert len(body['data']) == 2

            first_item = body['data'][0]
            assert first_item['date'] == '20241010'
            assert first_item['event_name'] == 'page_view'
            assert first_item['country'] == 'Brazil'
            assert first_item['host_name'] == 'simcc.uesc.br'
            assert first_item['event_count'] == 150
            assert first_item['active_users'] == 80

            summary = body['summary']
            assert summary['total_events'] == 195
            assert summary['total_active_users'] == 100
            assert summary['start_date'] == '30daysAgo'
            assert summary['end_date'] == 'today'
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.parametrize('path', ['/v2/analytics', '/v2/analytics/pages'])
@patch('simcc.v2.routers.analytics.BetaAnalyticsDataClient')
def test_analytics_api_error(mock_client_cls, path):
    """Retorna 502 se a chamada ao GA4 lançar exceção."""
    mock_client = MagicMock()
    mock_client.run_report.side_effect = RuntimeError('Conexão recusada')
    mock_client_cls.return_value = mock_client

    mock_settings = Settings(GA4_PROPERTY_ID='123456789')

    app.dependency_overrides[get_settings] = lambda: mock_settings
    try:
        with TestClient(app) as test_client:
            response = test_client.get(path)
            assert response.status_code == HTTPStatus.BAD_GATEWAY
            assert 'Falha na comunicação' in response.json()['detail']
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.parametrize(
    ('system', 'page_path'),
    [
        (None, '/simcc/indicadores'),
        ('ictite', '/ictite/v1/web/escolas'),
        ('licuri', '/licuri/indicadores'),
    ],
)
@patch('simcc.v2.routers.analytics.BetaAnalyticsDataClient')
def test_analytics_pages_success(mock_client_cls, system, page_path):
    """Filtra o módulo e ordena as visualizações por caminho no GA4."""
    mock_client = mock_client_cls.return_value
    mock_client.run_report.return_value = RunReportResponse(
        rows=[
            Row(
                dimension_values=[DimensionValue(value=page_path)],
                metric_values=[MetricValue(value='42')],
            )
        ],
        row_count=21,
    )
    settings = Settings(
        GA4_PROPERTY_ID='123456789', GA4_SITE_URL='observatorio.example'
    )

    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as test_client:
            params = {'limit': 1, 'offset': 15, 'start_date': '7daysAgo'}
            if system:
                params['system'] = system
            response = test_client.get('/v2/analytics/pages', params=params)
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'data': [
            {'page_path': page_path, 'page_views': 42},
        ],
        'total': 21,
    }
    request = mock_client.run_report.call_args.args[0]
    assert request.property == 'properties/123456789'
    assert request.date_ranges[0].start_date == '7daysAgo'
    assert request.date_ranges[0].end_date == 'today'
    assert [dimension.name for dimension in request.dimensions] == ['pagePath']
    assert [metric.name for metric in request.metrics] == ['screenPageViews']
    assert (request.limit, request.offset) == (1, 15)
    assert request.order_bys[0].metric.metric_name == 'screenPageViews'
    assert request.order_bys[0].desc
    assert request.order_bys[1].dimension.dimension_name == 'pagePath'

    page, host = request.dimension_filter.and_group.expressions
    assert page.filter.field_name == 'pagePath'
    path_filter = page.filter.string_filter
    assert path_filter.match_type == Filter.StringFilter.MatchType.FULL_REGEXP
    prefix = f'/{system or "simcc"}'
    assert re.fullmatch(path_filter.value, prefix)
    assert re.fullmatch(path_filter.value, f'{prefix}/')
    assert re.fullmatch(path_filter.value, page_path)
    assert not re.fullmatch(path_filter.value, '/outro-modulo')
    assert not re.fullmatch(path_filter.value, f'{prefix}-admin')
    assert host.filter.field_name == 'hostName'
    assert host.filter.string_filter.value == 'observatorio.example'


@patch('simcc.v2.routers.analytics.BetaAnalyticsDataClient')
def test_analytics_pages_empty(mock_client_cls):
    """A falta de visualizações é retornada como um relatório vazio."""
    mock_client_cls.return_value.run_report.return_value = RunReportResponse()
    settings = Settings(GA4_PROPERTY_ID='123456789', GA4_SITE_URL=None)

    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as test_client:
            response = test_client.get('/v2/analytics/pages')
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'data': [], 'total': 0}


@pytest.mark.parametrize(
    'query', ['limit=0', 'limit=101', 'offset=-1', 'system=outro-modulo']
)
def test_analytics_pages_invalid_query(query):
    """Rejeita sistemas e paginação inválidos antes de consultar o GA4."""
    with TestClient(app) as test_client:
        response = test_client.get(f'/v2/analytics/pages?{query}')

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
