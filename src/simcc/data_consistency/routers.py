from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select, update

from simcc.core.db.database import get_async_session
from simcc.core.dependencies import get_settings
from simcc.core.settings import Settings
from simcc.data_consistency.metrics import get_initial_metrics
from simcc.data_consistency.models import DataConsistencyResult, DataLoadRun
from simcc.data_consistency.schemas import (
    ConsistencyResultResponse,
    FailLoadRequest,
    FinishLoadRequest,
    LatestReportResponse,
    LoadHistoryItemResponse,
    LoadRunResponse,
    StartLoadRequest,
)
from simcc.data_consistency.services import (
    AFTER,
    BEFORE,
    RUNNING,
    capture_snapshot,
    compare_load_run,
)

router = APIRouter(prefix='/data-consistency', tags=['Data Consistency'])
internal_router = APIRouter(
    prefix='/internal/data-consistency', tags=['Data Consistency - Internal']
)


def _require_internal_api_key(
    api_key: Annotated[str | None, Header(alias='X-Internal-API-Key')] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Internal API key is not configured',
        )
    if api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid internal API key',
        )


@router.get('/latest', response_model=LatestReportResponse)
async def get_latest_report(session=Depends(get_async_session)):
    load = await session.scalar(
        select(DataLoadRun)
        .where(DataLoadRun.status == 'VALIDATED')
        .order_by(
            DataLoadRun.finished_at.desc().nulls_last(),
            DataLoadRun.started_at.desc(),
        )
        .limit(1)
    )
    if load is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No validated consistency report found',
        )

    metrics = (
        await session.execute(
            select(DataConsistencyResult)
            .where(DataConsistencyResult.load_run_id == load.id)
            .order_by(
                DataConsistencyResult.is_warning.desc(),
                DataConsistencyResult.metric_key,
                DataConsistencyResult.institution_name,
            )
        )
    ).scalars().all()
    return LatestReportResponse(
        load=load,
        summary={
            'total_metrics': len(metrics),
            'warnings': sum(metric.is_warning for metric in metrics),
            'normal': sum(metric.status == 'NORMAL' for metric in metrics),
            'new_scopes': sum(
                metric.status == 'NEW_SCOPE' for metric in metrics
            ),
        },
        metrics=metrics,
    )


@router.get('/history', response_model=list[LoadHistoryItemResponse])
async def get_load_history(  # noqa: PLR0913, PLR0917
    session=Depends(get_async_session),
    load_type: str | None = Query(default=None),
    load_status: str | None = Query(default=None, alias='status'),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    warning_count = func.count(DataConsistencyResult.id).filter(
        DataConsistencyResult.is_warning.is_(True)
    )
    result_count = func.count(DataConsistencyResult.id)
    statement = (
        select(DataLoadRun, warning_count, result_count)
        .outerjoin(
            DataConsistencyResult,
            DataConsistencyResult.load_run_id == DataLoadRun.id,
        )
        .group_by(DataLoadRun.id)
        .order_by(DataLoadRun.started_at.desc())
        .limit(limit)
    )
    if load_type:
        statement = statement.where(DataLoadRun.load_type == load_type)
    if load_status:
        statement = statement.where(DataLoadRun.status == load_status)
    if date_from:
        statement = statement.where(DataLoadRun.started_at >= date_from)
    if date_to:
        statement = statement.where(DataLoadRun.started_at <= date_to)

    rows = (await session.execute(statement)).all()
    return [
        LoadHistoryItemResponse(
            id=load.id,
            load_type=load.load_type,
            status=load.status,
            trigger_source=load.trigger_source,
            started_at=load.started_at,
            finished_at=load.finished_at,
            error_detail=load.error_detail,
            warning_count=warning,
            result_count=results,
        )
        for load, warning, results in rows
    ]


@router.get('/loads/latest', response_model=list[LoadRunResponse])
async def get_latest_loads(session=Depends(get_async_session)):
    latest = (
        select(
            DataLoadRun.load_type,
            func.max(DataLoadRun.started_at).label('latest_started_at'),
        )
        .group_by(DataLoadRun.load_type)
        .subquery()
    )
    rows = (
        await session.execute(
            select(DataLoadRun)
            .join(
                latest,
                (DataLoadRun.load_type == latest.c.load_type)
                & (
                    DataLoadRun.started_at == latest.c.latest_started_at
                ),
            )
            .order_by(DataLoadRun.load_type)
        )
    ).scalars().all()
    return rows


@internal_router.post(
    '/loads',
    response_model=LoadRunResponse,
    dependencies=[Depends(_require_internal_api_key)],
)
async def start_load(
    request: StartLoadRequest,
    session=Depends(get_async_session),
):
    load = DataLoadRun(
        load_type=request.load_type,
        trigger_source=request.trigger_source,
        status=RUNNING,
    )
    session.add(load)
    await session.flush()
    await capture_snapshot(
        session,
        load.id,
        BEFORE,
        await get_initial_metrics(session),
    )
    await session.commit()
    return load


@internal_router.post(
    '/loads/{load_id}/finish',
    response_model=list[ConsistencyResultResponse],
    dependencies=[Depends(_require_internal_api_key)],
)
async def finish_load(
    load_id: UUID,
    request: FinishLoadRequest,
    session=Depends(get_async_session),
):
    load = await session.get(DataLoadRun, load_id)
    if load is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Load execution not found',
        )
    if load.status != 'RUNNING':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Load execution is already {load.status}',
        )
    try:
        await capture_snapshot(
            session,
            load_id,
            AFTER,
            await get_initial_metrics(session),
        )
        results = await compare_load_run(
            session,
            load_id,
            lower_tolerance=request.lower_tolerance,
            upper_tolerance=request.upper_tolerance,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    await session.commit()
    return results


@internal_router.post(
    '/loads/{load_id}/fail',
    response_model=LoadRunResponse,
    dependencies=[Depends(_require_internal_api_key)],
)
async def fail_load(
    load_id: UUID,
    request: FailLoadRequest,
    session=Depends(get_async_session),
):
    result = await session.execute(
        update(DataLoadRun)
        .where(DataLoadRun.id == load_id, DataLoadRun.status == 'RUNNING')
        .values(
            status='FAILED',
            error_detail=request.error_detail,
            finished_at=func.now(),
        )
        .returning(DataLoadRun)
    )
    load = result.scalar_one_or_none()
    if load is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Running load execution not found',
        )
    await session.commit()
    return load
