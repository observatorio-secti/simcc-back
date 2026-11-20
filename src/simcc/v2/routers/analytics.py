"""Router para métricas do Google Analytics 4 v2."""

import os
import time
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    FilterExpressionList,
    Metric,
    OrderBy,
    RunReportRequest,
    RunReportResponse,
)

from simcc.core.dependencies import get_settings
from simcc.core.settings import Settings
from simcc.v2.schemas.analytics import (
    AnalyticsMetricItem,
    AnalyticsPageMetric,
    AnalyticsPagesParams,
    AnalyticsPagesResponse,
    AnalyticsParams,
    AnalyticsResponse,
    AnalyticsSummary,
)
from simcc.v2.schemas.envelope import LIST_ERROR_RESPONSES, Meta
from simcc.v2.schemas.query import as_query, forbid_unknown_params

router = APIRouter(tags=['Analytics v2'])

DEFAULT_GOOGLE_CREDENTIALS_PATH = 'google_credentials.json'


def _get_analytics_client(
    credentials_path: str | None = DEFAULT_GOOGLE_CREDENTIALS_PATH,
) -> BetaAnalyticsDataClient:
    """Instancia o cliente do GA4 utilizando o arquivo de credenciais."""
    resolved_path = None
    if credentials_path and os.path.exists(credentials_path):
        resolved_path = credentials_path
    elif os.path.exists(DEFAULT_GOOGLE_CREDENTIALS_PATH):
        resolved_path = DEFAULT_GOOGLE_CREDENTIALS_PATH

    if resolved_path:
        os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', resolved_path)

    return BetaAnalyticsDataClient()


def _get_property(settings: Settings) -> str:
    if not settings.GA4_PROPERTY_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='GA4_PROPERTY_ID não configurado no servidor.',
        )
    return f'properties/{settings.GA4_PROPERTY_ID}'


def _run_report(request: RunReportRequest) -> RunReportResponse:
    try:
        client = _get_analytics_client()
        return client.run_report(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Falha na comunicação com o Google Analytics: {exc}',
        ) from exc


def _string_filter(
    field_name: str,
    value: str,
    match_type: Filter.StringFilter.MatchType = (
        Filter.StringFilter.MatchType.EXACT
    ),
) -> FilterExpression:
    return FilterExpression(
        filter=Filter(
            field_name=field_name,
            string_filter=Filter.StringFilter(
                match_type=match_type, value=value
            ),
        )
    )


@router.get(
    '/analytics',
    response_model=AnalyticsResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[Depends(forbid_unknown_params(AnalyticsParams))],
)
def get_analytics_metrics(  # noqa: PLR0914
    params: Annotated[AnalyticsParams, Depends(as_query(AnalyticsParams))],
    settings: Settings = Depends(get_settings),
) -> AnalyticsResponse:
    """Consulta métricas consolidadas do GA4."""
    property_name = _get_property(settings)
    target_host = params.host_name or settings.GA4_SITE_URL
    filters = []
    if target_host:
        filters.append(_string_filter('hostName', target_host))
    if params.event_name:
        filters.append(_string_filter('eventName', params.event_name))

    dimension_filter = None
    if len(filters) == 1:
        dimension_filter = filters[0]
    elif len(filters) > 1:
        dimension_filter = FilterExpression(
            and_group=FilterExpressionList(expressions=filters)
        )

    request = RunReportRequest(
        property=property_name,
        date_ranges=[
            DateRange(start_date=params.start_date, end_date=params.end_date)
        ],
        dimensions=[
            Dimension(name='date'),
            Dimension(name='eventName'),
            Dimension(name='country'),
            Dimension(name='hostName'),
        ],
        metrics=[
            Metric(name='eventCount'),
            Metric(name='activeUsers'),
        ],
        order_bys=[
            OrderBy(
                dimension=OrderBy.DimensionOrderBy(dimension_name='date'),
                desc=False,
            )
        ],
        dimension_filter=dimension_filter,
    )

    response = _run_report(request)

    items: list[AnalyticsMetricItem] = []
    total_events = 0
    total_active_users = 0

    for row in response.rows:
        date_val = row.dimension_values[0].value
        event_name_val = row.dimension_values[1].value
        country_val = row.dimension_values[2].value
        host_val = row.dimension_values[3].value

        event_count = int(row.metric_values[0].value or 0)
        active_users = int(row.metric_values[1].value or 0)

        total_events += event_count
        total_active_users += active_users

        items.append(
            AnalyticsMetricItem(
                date=_parse_ga_date(date_val),
                event_name=event_name_val,
                country=country_val,
                host_name=host_val,
                event_count=event_count,
                active_users=active_users,
            )
        )

    return AnalyticsResponse(
        data=items,
        summary=AnalyticsSummary(
            total_events=total_events,
            total_active_users=total_active_users,
            start_date=params.start_date,
            end_date=params.end_date,
        ),
        meta=Meta(
            took_ms=int((time.perf_counter() - start_time) * 1000),
            cached=False,
            timestamp=datetime.now(timezone.utc),
        ),
    )


@router.get(
    '/analytics/pages',
    response_model=AnalyticsPagesResponse,
    dependencies=[Depends(forbid_unknown_params(AnalyticsPagesParams))],
)
def get_analytics_pages(
    params: Annotated[
        AnalyticsPagesParams, Depends(as_query(AnalyticsPagesParams))
    ],
    settings: Settings = Depends(get_settings),
) -> AnalyticsPagesResponse:
    """Lista os caminhos de um sistema por visualizações no GA4."""
    page_filter = _string_filter(
        'pagePath',
        f'/{params.system}(/.*)?',
        Filter.StringFilter.MatchType.FULL_REGEXP,
    )
    target_host = params.host_name or settings.GA4_SITE_URL
    dimension_filter = page_filter
    if target_host:
        dimension_filter = FilterExpression(
            and_group=FilterExpressionList(
                expressions=[
                    page_filter,
                    _string_filter('hostName', target_host),
                ]
            )
        )

    request = RunReportRequest(
        property=_get_property(settings),
        date_ranges=[
            DateRange(start_date=params.start_date, end_date=params.end_date)
        ],
        dimensions=[Dimension(name='pagePath')],
        metrics=[Metric(name='screenPageViews')],
        dimension_filter=dimension_filter,
        order_bys=[
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name='screenPageViews'),
                desc=True,
            ),
            OrderBy(
                dimension=OrderBy.DimensionOrderBy(dimension_name='pagePath')
            ),
        ],
        limit=params.limit,
        offset=params.offset,
    )
    response = _run_report(request)
    return AnalyticsPagesResponse(
        data=[
            AnalyticsPageMetric(
                page_path=row.dimension_values[0].value,
                page_views=int(row.metric_values[0].value or 0),
            )
            for row in response.rows
        ],
        total=response.row_count,
    )
