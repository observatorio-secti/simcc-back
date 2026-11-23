from collections.abc import Iterable
from decimal import Decimal
from typing import Final
from uuid import UUID

from sqlalchemy import delete, func, select, update

from simcc.data_consistency.comparison import (
    DEFAULT_LOWER_TOLERANCE,
    DEFAULT_UPPER_TOLERANCE,
    compare_values,
)
from simcc.data_consistency.metrics import MetricValue, get_initial_metrics
from simcc.data_consistency.models import (
    DataConsistencyResult,
    DataLoadRun,
    DataSnapshotMetric,
)

BEFORE: Final = 'BEFORE'
AFTER: Final = 'AFTER'
VALIDATED: Final = 'VALIDATED'
RUNNING: Final = 'RUNNING'


async def capture_snapshot(
    session,
    load_run_id: UUID,
    phase: str,
    metrics: Iterable[MetricValue] | None = None,
) -> list[DataSnapshotMetric]:
    """Persist one complete metric snapshot for a load execution."""
    if phase not in {BEFORE, AFTER}:
        raise ValueError(f'Unsupported snapshot phase: {phase}')

    load_run = await session.get(DataLoadRun, load_run_id)
    if load_run is None:
        raise ValueError(f'Load execution not found: {load_run_id}')
    if load_run.status != RUNNING:
        raise ValueError(
            f'Cannot capture snapshot for load with status {load_run.status}'
        )

    metric_values = list(
        metrics if metrics is not None else await get_initial_metrics(session)
    )
    if not metric_values:
        raise ValueError('Cannot persist an empty metric snapshot')

    await session.execute(
        delete(DataSnapshotMetric).where(
            DataSnapshotMetric.load_run_id == load_run_id,
            DataSnapshotMetric.phase == phase,
        )
    )

    snapshot = [
        DataSnapshotMetric(
            load_run_id=load_run_id,
            phase=phase,
            metric_key=metric.metric_key,
            scope=metric.scope,
            value_numeric=metric.value,
            institution_id=metric.institution_id,
            institution_name=metric.institution_name,
        )
        for metric in metric_values
    ]
    session.add_all(snapshot)
    await session.flush()
    return snapshot


async def compare_load_run(
    session,
    load_run_id: UUID,
    *,
    lower_tolerance: Decimal = DEFAULT_LOWER_TOLERANCE,
    upper_tolerance: Decimal = DEFAULT_UPPER_TOLERANCE,
) -> list[DataConsistencyResult]:
    """Compare persisted BEFORE and AFTER snapshots for one load."""
    load_run = await session.get(DataLoadRun, load_run_id)
    if load_run is None:
        raise ValueError(f'Load execution not found: {load_run_id}')
    if load_run.status != RUNNING:
        raise ValueError(
            f'Cannot compare load with status {load_run.status}'
        )

    snapshots = (
        await session.execute(
            select(DataSnapshotMetric).where(
                DataSnapshotMetric.load_run_id == load_run_id
            )
        )
    ).scalars().all()
    by_phase = {
        phase: {
            _metric_identity(metric): metric
            for metric in snapshots
            if metric.phase == phase
        }
        for phase in (BEFORE, AFTER)
    }
    if not by_phase[BEFORE] or not by_phase[AFTER]:
        raise ValueError('Both BEFORE and AFTER snapshots are required')

    identities = set(by_phase[BEFORE]) | set(by_phase[AFTER])
    results: list[DataConsistencyResult] = []
    for identity in sorted(identities, key=str):
        before = by_phase[BEFORE].get(identity)
        after = by_phase[AFTER].get(identity)
        before_value = before.value_numeric if before else 0
        after_value = after.value_numeric if after else 0
        comparison = compare_values(
            before_value,
            after_value,
            lower_tolerance=lower_tolerance,
            upper_tolerance=upper_tolerance,
        )
        source = after or before
        results.append(
            DataConsistencyResult(
                load_run_id=load_run_id,
                metric_key=source.metric_key,
                scope=source.scope,
                institution_id=source.institution_id,
                institution_name=source.institution_name,
                before_value=comparison.before_value,
                after_value=comparison.after_value,
                absolute_difference=comparison.absolute_difference,
                status=comparison.status,
                variation_percent=comparison.variation_percent,
                lower_threshold=comparison.lower_tolerance,
                upper_threshold=comparison.upper_tolerance,
                is_warning=comparison.is_warning,
                warning_reason=comparison.warning_reason,
            )
        )

    await session.execute(
        delete(DataConsistencyResult).where(
            DataConsistencyResult.load_run_id == load_run_id
        )
    )
    session.add_all(results)
    await session.execute(
        update(DataLoadRun)
        .where(DataLoadRun.id == load_run_id)
        .values(status=VALIDATED, finished_at=func.now())
    )
    await session.flush()
    return results


def _metric_identity(metric: DataSnapshotMetric) -> tuple:
    return (
        metric.metric_key,
        metric.scope,
        metric.institution_id,
    )
