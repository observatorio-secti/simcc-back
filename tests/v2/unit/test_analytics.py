# ruff: noqa: PLR2004, PLR0913, PLR0917
"""Testes unitários para o endpoint de métricas do GA4 v2."""

from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

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


@patch('simcc.v2.routers.analytics.BetaAnalyticsDataClient')
def test_analytics_api_error(mock_client_cls):
    """Retorna 502 se a chamada ao GA4 lançar exceção."""
    mock_client = MagicMock()
    mock_client.run_report.side_effect = RuntimeError('Conexão recusada')
    mock_client_cls.return_value = mock_client

    mock_settings = Settings(GA4_PROPERTY_ID='123456789')

    app.dependency_overrides[get_settings] = lambda: mock_settings
    try:
        with TestClient(app) as test_client:
            response = test_client.get('/v2/analytics')
            assert response.status_code == HTTPStatus.BAD_GATEWAY
            assert 'Falha na comunicação' in response.json()['detail']
    finally:
        app.dependency_overrides.pop(get_settings, None)
