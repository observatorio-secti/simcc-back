from decimal import Decimal

import pytest

from simcc.core.db.models import DataLoadRun
from simcc.data_consistency.metrics import (
    GLOBAL,
    RESEARCHERS_TOTAL,
    MetricValue,
)
from simcc.data_consistency.services import (
    AFTER,
    BEFORE,
    capture_snapshot,
    compare_load_run,
)


@pytest.mark.asyncio
async def test_capture_and_compare_persist_results(session):
    before_value = 100
    after_value = 92
    load = DataLoadRun(
        load_type='LATTES',
        trigger_source='TEST',
        status='RUNNING',
    )
    session.add(load)
    await session.flush()

    await capture_snapshot(
        session,
        load.id,
        BEFORE,
        [
            MetricValue(
                metric_key=RESEARCHERS_TOTAL,
                scope=GLOBAL,
                value=before_value,
            )
        ],
    )
    await capture_snapshot(
        session,
        load.id,
        AFTER,
        [
            MetricValue(
                metric_key=RESEARCHERS_TOTAL,
                scope=GLOBAL,
                value=after_value,
            )
        ],
    )

    results = await compare_load_run(session, load.id)
    await session.commit()

    assert len(results) == 1
    assert results[0].before_value == before_value
    assert results[0].after_value == after_value
    assert results[0].variation_percent == Decimal('-8.0000')
    assert results[0].is_warning is True
    assert load.status == 'VALIDATED'
    await session.refresh(load)
    assert load.finished_at is not None


@pytest.mark.asyncio
async def test_compare_treats_missing_institution_as_new_scope(
    session, institution_factory
):
    institution = await institution_factory(name='New University')
    load = DataLoadRun(
        load_type='LATTES',
        trigger_source='TEST',
        status='RUNNING',
    )
    session.add(load)
    await session.flush()

    before_metric = MetricValue(
        metric_key=RESEARCHERS_TOTAL,
        scope='INSTITUTION',
        value=0,
        institution_id=institution.id,
        institution_name=institution.name,
    )
    after_metric = MetricValue(
        metric_key=RESEARCHERS_TOTAL,
        scope='INSTITUTION',
        value=25,
        institution_id=institution.id,
        institution_name=institution.name,
    )
    await capture_snapshot(session, load.id, BEFORE, [before_metric])
    await capture_snapshot(session, load.id, AFTER, [after_metric])

    results = await compare_load_run(session, load.id)

    assert results[0].status == 'NEW_SCOPE'
    assert results[0].variation_percent is None
    assert results[0].is_warning is False
