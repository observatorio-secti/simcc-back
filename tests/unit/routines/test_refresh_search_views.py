# ruff: noqa: PLR2004
from unittest.mock import MagicMock

import pytest

import scripts.routines.refresh_search_views as rsv


@pytest.mark.unit
def test_refresh_views_success():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    ctx_mock = mock_engine.connect.return_value.execution_options.return_value
    ctx_mock.__enter__.return_value = mock_conn

    rsv.refresh_views(engine=mock_engine)

    assert rsv.items_found == 5
    assert rsv.items_succeeded == 5
    assert rsv.items_failed == 0

    # Valida se execution_options recebeu AUTOCOMMIT
    mock_engine.connect.return_value.execution_options.assert_called_once_with(
        isolation_level='AUTOCOMMIT'
    )

    # Valida chamadas de SQL para cada MV na ordem correta
    executed_sqls = [
        str(call[0][0]) for call in mock_conn.execute.call_args_list
    ]
    assert len(executed_sqls) == 5
    assert (
        'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_articles'
        in executed_sqls[0]
    )
    assert (
        'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_books'
        in executed_sqls[1]
    )
    assert (
        'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_patents'
        in executed_sqls[2]
    )
    assert (
        'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_software'
        in executed_sqls[3]
    )
    assert (
        'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_researcher_search'
        in executed_sqls[4]
    )


@pytest.mark.unit
def test_refresh_views_error():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = RuntimeError('PostgreSQL connection drop')
    ctx_mock = mock_engine.connect.return_value.execution_options.return_value
    ctx_mock.__enter__.return_value = mock_conn

    with pytest.raises(RuntimeError, match='PostgreSQL connection drop'):
        rsv.refresh_views(engine=mock_engine)

    assert rsv.items_failed == 5
    assert rsv.items_succeeded == 0
