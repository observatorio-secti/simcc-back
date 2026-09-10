from typing import Optional

from pydantic import field_validator
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
    OPENAI_API_KEY: Optional[str] = None
    FIREBASE_COLLECTION: str = 'termos_busca'
    INTERNAL_API_KEY: Optional[str] = None
    LOG_STREAM_TOKEN: Optional[str] = None

    FIREBASE_CERT_PATH: str = 'cert.json'

    XML_PATH: str = 'storage/xml'
    CURRENT_XML_PATH: str = 'storage/xml/current'
    ZIP_XML_PATH: str = 'storage/xml/current'

    ALTERNATIVE_CNPQ_SERVICE: bool = False

    APPLICATION: str = 'simcc'
    ENVIRONMENT: str = 'development'
    LOG_LEVEL: str = 'INFO'
    LOG_DIR: str = 'logs'
    LOG_RETENTION_DAYS: int = 7

    # Configurações de Cache (Redis)
    REDIS_URL: str = 'redis://localhost:6379/0'
    REDIS_ENABLED: bool = True

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

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
