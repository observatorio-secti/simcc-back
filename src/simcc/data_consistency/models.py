from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from simcc.core.db.models.base import table_registry


@table_registry.mapped_as_dataclass
class DataLoadRun:
    """A single execution of a data load and its consistency validation."""

    __tablename__ = 'data_load_run'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    load_type: Mapped[str] = mapped_column(String(80))
    trigger_source: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(
        String(30), server_default=text("'RUNNING'")
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text('now()'), init=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )
    error_detail: Mapped[Optional[str]] = mapped_column(
        Text, default=None
    )

    __table_args__ = (
        Index(
            'idx_data_load_run_type_started',
            'load_type',
            'started_at',
        ),
        Index('idx_data_load_run_status', 'status'),
    )


@table_registry.mapped_as_dataclass
class DataSnapshotMetric:
    """A metric captured before or after a load."""

    __tablename__ = 'data_snapshot_metric'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    load_run_id: Mapped[UUID] = mapped_column(
        ForeignKey('data_load_run.id', ondelete='CASCADE')
    )
    phase: Mapped[str] = mapped_column(String(10))
    metric_key: Mapped[str] = mapped_column(String(100))
    scope: Mapped[str] = mapped_column(String(20))
    value_numeric: Mapped[int] = mapped_column(BigInteger)
    institution_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('institution.id', ondelete='SET NULL'), default=None
    )
    institution_name: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text('now()'), init=False
    )

    __table_args__ = (
        UniqueConstraint(
            'load_run_id',
            'phase',
            'metric_key',
            'scope',
            'institution_id',
            name='uq_data_snapshot_metric_identity',
        ),
        Index(
            'idx_data_snapshot_metric_run_phase',
            'load_run_id',
            'phase',
        ),
        Index(
            'idx_data_snapshot_metric_lookup',
            'metric_key',
            'scope',
            'institution_id',
        ),
    )


@table_registry.mapped_as_dataclass
class DataConsistencyResult:
    """Comparison result between the before and after snapshots."""

    __tablename__ = 'data_consistency_result'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    load_run_id: Mapped[UUID] = mapped_column(
        ForeignKey('data_load_run.id', ondelete='CASCADE')
    )
    metric_key: Mapped[str] = mapped_column(String(100))
    scope: Mapped[str] = mapped_column(String(20))
    before_value: Mapped[int] = mapped_column(BigInteger)
    after_value: Mapped[int] = mapped_column(BigInteger)
    absolute_difference: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(30))
    institution_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('institution.id', ondelete='SET NULL'), default=None
    )
    institution_name: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    variation_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4), default=None
    )
    lower_threshold: Mapped[Decimal] = mapped_column(
        Numeric(6, 3), server_default=text('5'), default=Decimal('5')
    )
    upper_threshold: Mapped[Decimal] = mapped_column(
        Numeric(6, 3), server_default=text('10'), default=Decimal('10')
    )
    is_warning: Mapped[bool] = mapped_column(
        server_default=text('false'), default=False
    )
    warning_reason: Mapped[Optional[str]] = mapped_column(
        Text, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text('now()'), init=False
    )

    __table_args__ = (
        UniqueConstraint(
            'load_run_id',
            'metric_key',
            'scope',
            'institution_id',
            name='uq_data_consistency_result_identity',
        ),
        Index(
            'idx_data_consistency_result_run_warning',
            'load_run_id',
            'is_warning',
        ),
        Index(
            'idx_data_consistency_result_metric_scope',
            'metric_key',
            'scope',
            'institution_id',
        ),
    )
