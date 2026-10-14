"""Router para métricas do Google Analytics 4 v2."""

import os
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
)

from simcc.core.dependencies import get_settings
from simcc.core.settings import Settings
from simcc.v2.schemas.analytics import (
    AnalyticsMetricItem,
    AnalyticsParams,
    AnalyticsResponse,
    AnalyticsSummary,
)
from simcc.v2.schemas.query import as_query, forbid_unknown_params

router = APIRouter(tags=['Analytics v2'])


def _get_analytics_client(
    credentials_path: str | None,
) -> BetaAnalyticsDataClient:
    """Instancia o cliente do GA4 utilizando o arquivo de credenciais."""
    resolved_path = None
    if credentials_path and os.path.exists(credentials_path):
        resolved_path = credentials_path
    elif os.path.exists('google_credentials.json'):
        resolved_path = 'google_credentials.json'

    if resolved_path:
        os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', resolved_path)

    return BetaAnalyticsDataClient()


@router.get(
    '/analytics',
    response_model=AnalyticsResponse,
    dependencies=[Depends(forbid_unknown_params(AnalyticsParams))],
)
def get_analytics_metrics(
    params: Annotated[AnalyticsParams, Depends(as_query(AnalyticsParams))],
    settings: Settings = Depends(get_settings),
) -> AnalyticsResponse:
    """Consulta métricas consolidadas do GA4."""
    if not settings.GA4_PROPERTY_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='GA4_PROPERTY_ID não configurado no servidor.',
        )

    target_host = params.host_name or settings.GA4_SITE_URL
    filters = []
    if target_host:
        filters.append(
            FilterExpression(
                filter=Filter(
                    field_name='hostName',
                    string_filter=Filter.StringFilter(
                        match_type=Filter.StringFilter.MatchType.EXACT,
                        value=target_host,
                    ),
                )
            )
        )
    if params.event_name:
        filters.append(
            FilterExpression(
                filter=Filter(
                    field_name='eventName',
                    string_filter=Filter.StringFilter(
                        match_type=Filter.StringFilter.MatchType.EXACT,
                        value=params.event_name,
                    ),
                )
            )
        )

    dimension_filter = None
    if len(filters) == 1:
        dimension_filter = filters[0]
    elif len(filters) > 1:
        dimension_filter = FilterExpression(
            and_group=FilterExpressionList(expressions=filters)
        )

    request = RunReportRequest(
        property=f'properties/{settings.GA4_PROPERTY_ID}',
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

    try:
        client = _get_analytics_client(settings.GOOGLE_APPLICATION_CREDENTIALS)
        response = client.run_report(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Falha na comunicação com o Google Analytics: {exc}',
        ) from exc

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
                date=date_val,
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
    )
