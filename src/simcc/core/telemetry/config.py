from dataclasses import dataclass
from typing import Literal, Optional

from simcc.core.settings import Settings

ExporterType = Literal['console', 'otlp', 'in_memory', 'none']


@dataclass(frozen=True)
class TelemetryConfig:
    enabled: bool
    exporter_type: ExporterType
    otlp_endpoint: str
    otlp_insecure: bool
    sampling_ratio: float
    service_name: str
    service_namespace: str
    service_version: str
    environment: str
    metrics_exporter_type: Optional[ExporterType] = None


def get_telemetry_config() -> TelemetryConfig:
    settings = Settings()

    exporter_raw = getattr(settings, 'OTEL_EXPORTER_TYPE', 'none').lower()
    if exporter_raw not in {'console', 'otlp', 'in_memory', 'none'}:
        exporter_raw = 'none'

    metrics_exporter_raw = getattr(
        settings, 'OTEL_METRICS_EXPORTER_TYPE', 'none'
    ).lower()
    if metrics_exporter_raw not in {'console', 'otlp', 'in_memory', 'none'}:
        metrics_exporter_raw = 'none'

    return TelemetryConfig(
        enabled=getattr(settings, 'OTEL_ENABLED', True),
        exporter_type=exporter_raw,  # type: ignore[arg-type]
        metrics_exporter_type=metrics_exporter_raw,  # type: ignore[arg-type]
        otlp_endpoint=getattr(
            settings, 'OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317'
        ),
        otlp_insecure=getattr(settings, 'OTEL_EXPORTER_OTLP_INSECURE', True),
        sampling_ratio=float(getattr(settings, 'OTEL_SAMPLING_RATIO', 1.0)),
        service_name=getattr(settings, 'OTEL_SERVICE_NAME', 'simcc-back'),
        service_namespace=getattr(settings, 'OTEL_SERVICE_NAMESPACE', 'simcc'),
        service_version='4.5.0',
        environment=getattr(settings, 'ENVIRONMENT', 'development'),
    )
