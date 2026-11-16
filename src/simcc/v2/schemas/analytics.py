"""Schemas para o endpoint de métricas do Google Analytics 4 v2."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class AnalyticsReportParams(BaseModel):
    start_date: str = Field(
        '30daysAgo',
        description=(
            'Data de início no formato YYYY-MM-DD ou relativo '
            "(ex: '30daysAgo', '7daysAgo')"
        ),
    )
    end_date: str = Field(
        'today',
        description=(
            'Data de término no formato YYYY-MM-DD ou relativo '
            "(ex: 'today', 'yesterday')"
        ),
    )
    host_name: Optional[str] = Field(
        None,
        description=(
            'Host/domínio a filtrar. Se omitido, utiliza a URL padrão do site'
        ),
    )


class AnalyticsParams(AnalyticsReportParams):
    event_name: Optional[str] = Field(
        None,
        description="Filtro opcional pelo nome do evento (ex: 'page_view')",
    )


class AnalyticsPagesParams(AnalyticsReportParams):
    system: Literal['simcc', 'ictite', 'licuri'] = Field(
        'simcc', description='Sistema do Observatório a consultar'
    )
    limit: int = Field(15, ge=1, le=100, description='Linhas por página')
    offset: int = Field(
        0, ge=0, le=2_147_483_647, description='Posição da primeira linha'
    )


class AnalyticsPageMetric(BaseModel):
    page_path: str = Field(description='Caminho da página sem parâmetros')
    page_views: int = Field(description='Visualizações no período')


class AnalyticsPagesResponse(BaseModel):
    data: list[AnalyticsPageMetric]
    total: int = Field(description='Total de caminhos em todas as páginas')


class AnalyticsMetricItem(BaseModel):
    date: str = Field(description='Data da ocorrência (formato YYYYMMDD)')
    event_name: str = Field(description='Nome do evento registrado no GA4')
    country: str = Field(description='País de origem do acesso')
    host_name: str = Field(description='Host do site acessado')
    event_count: int = Field(description='Quantidade de eventos disparados')
    active_users: int = Field(description='Quantidade de usuários ativos')


class AnalyticsSummary(BaseModel):
    total_events: int = Field(
        description='Total acumulado de eventos no período'
    )
    total_active_users: int = Field(
        description='Total acumulado de usuários ativos'
    )
    start_date: str
    end_date: str


class AnalyticsResponse(BaseModel):
    data: list[AnalyticsMetricItem] = Field(
        description='Lista de métricas detalhadas'
    )
    summary: AnalyticsSummary = Field(description='Resumo do período')
