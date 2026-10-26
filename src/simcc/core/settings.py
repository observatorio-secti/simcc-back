from typing import Optional
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings, extra='ignore'):
    DATABASE_URL: str
    ADMIN_DATABASE_URL: str

    CORS_ALLOW_ORIGINS: list[str] = ['*']
    CORS_ALLOW_METHODS: list[str] = ['*']
    CORS_ALLOW_HEADERS: list[str] = ['*']
    CORS_ALLOW_CREDENTIALS: bool = True

    ADMIN_URL: str = 'http://localhost:0000/'
    URL: str = 'http://localhost:0000/'
    ROOT_PATH: str = Field(
        default='',
        validation_alias=AliasChoices(
            'ROOT_PATH', 'API_ROOT_PATH', 'FASTAPI_ROOT_PATH'
        ),
    )
    OPENAI_API_KEY: Optional[str] = None
    INTERNAL_API_KEY: Optional[str] = None
    LOG_STREAM_TOKEN: Optional[str] = None

    XML_PATH: str = 'storage/xml'
    CURRENT_XML_PATH: str = 'storage/xml/current'
    ZIP_XML_PATH: str = 'storage/xml/current'

    ALTERNATIVE_CNPQ_SERVICE: bool = False

    APPLICATION: str = 'simcc'
    ENVIRONMENT: str = 'development'
    LOG_LEVEL: str = 'INFO'
    LOG_DIR: str = 'logs'
    LOG_RETENTION_DAYS: int = 7

    # Open DGP API (ODA) - fonte dos grupos de pesquisa do Power BI
    ODA_API_URL: str = 'https://oda.vertb.com.br'
    ODA_RESEARCH_GROUPS_PATH: str = (
        'storage/powerBI/oda_research_groups.parquet'
    )

    # Configurações de Cache (Redis)
    REDIS_URL: str = 'redis://localhost:6379/0'
    REDIS_ENABLED: bool = True
    # A invalidação acontece a cada refresh das MVs; o TTL só limita memória
    V2_SEARCH_CACHE_TTL: int = 21600

    # Configurações de IA e Qualidade
    AI_COSINE_DISTANCE_THRESHOLD: float = 0.65
    AI_CACHE_TTL: int = 3600

    # Configurações de Telemetria (OpenTelemetry)
    OTEL_ENABLED: bool = True
    OTEL_EXPORTER_TYPE: str = 'none'
    OTEL_METRICS_EXPORTER_TYPE: str = 'none'
    OTEL_EXPORTER_OTLP_ENDPOINT: str = 'http://localhost:4317'
    OTEL_EXPORTER_OTLP_INSECURE: bool = True
    OTEL_SAMPLING_RATIO: float = 1.0
    OTEL_SERVICE_NAME: str = 'simcc-back'
    OTEL_SERVICE_NAMESPACE: str = 'simcc'

    # Configurações do Google Analytics 4 (GA4)
    GA4_PROPERTY_ID: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            'GA4_PROPERTY_ID', 'VITE_GA4_PROPERTY_ID'
        ),
    )
    GA4_SITE_URL: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('GA4_SITE_URL', 'VITE_URL_SITE'),
    )
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = 'google_credentials.json'

    @field_validator(
        'CORS_ALLOW_ORIGINS',
        'CORS_ALLOW_METHODS',
        'CORS_ALLOW_HEADERS',
        mode='before',
    )
    @classmethod
    def assemble_cors_list(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith('['):
            return [i.strip() for i in v.split(',') if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @field_validator('ROOT_PATH', mode='before')
    @classmethod
    def assemble_root_path(cls, v: Optional[str]) -> str:
        if v:
            path = v.strip().rstrip('/')
            if path and not path.startswith('/'):
                path = f'/{path}'
            return path
        return ''

    @model_validator(mode='after')
    def set_default_root_path(self) -> 'Settings':
        if not self.ROOT_PATH and self.URL:
            path = urlparse(self.URL).path.rstrip('/')
            if path:
                self.ROOT_PATH = path
        return self

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
