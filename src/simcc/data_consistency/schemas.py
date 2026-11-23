from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoadRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    load_type: str
    status: str
    trigger_source: str
    started_at: datetime
    finished_at: datetime | None
    error_detail: str | None


class ConsistencyResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    load_run_id: UUID
    metric_key: str
    scope: str
    institution_id: UUID | None
    institution_name: str | None
    before_value: int
    after_value: int
    absolute_difference: int
    variation_percent: Decimal | None
    lower_threshold: Decimal
    upper_threshold: Decimal
    status: str
    is_warning: bool
    warning_reason: str | None


class LatestReportResponse(BaseModel):
    load: LoadRunResponse
    summary: dict[str, int]
    metrics: list[ConsistencyResultResponse]


class LoadHistoryItemResponse(LoadRunResponse):
    warning_count: int = Field(ge=0)
    result_count: int = Field(ge=0)


class StartLoadRequest(BaseModel):
    load_type: str = Field(min_length=1, max_length=80)
    trigger_source: str = Field(min_length=1, max_length=30)


class FinishLoadRequest(BaseModel):
    lower_tolerance: Decimal = Field(default=Decimal('5'), ge=0)
    upper_tolerance: Decimal = Field(default=Decimal('10'), ge=0)


class FailLoadRequest(BaseModel):
    error_detail: str = Field(min_length=1)
