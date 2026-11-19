from sqlalchemy import inspect

from simcc.core.db.models import (
    DataConsistencyResult,
    DataLoadRun,
    DataSnapshotMetric,
)


def test_data_consistency_models_are_registered():
    assert DataLoadRun.__tablename__ == 'data_load_run'
    assert DataSnapshotMetric.__tablename__ == 'data_snapshot_metric'
    assert DataConsistencyResult.__tablename__ == 'data_consistency_result'


def test_snapshot_and_result_have_identity_constraints():
    snapshot_constraints = {
        constraint.name
        for constraint in inspect(DataSnapshotMetric).local_table.constraints
    }
    result_constraints = {
        constraint.name
        for constraint in inspect(
            DataConsistencyResult
        ).local_table.constraints
    }

    assert 'uq_data_snapshot_metric_identity' in snapshot_constraints
    assert 'uq_data_consistency_result_identity' in result_constraints
