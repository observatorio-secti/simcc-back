# ruff: noqa: PLW0603
from sqlalchemy import text

from simcc.core.db.database import sync_engine
from simcc.core.logging import logger
from simcc.core.logging.events import (
    routine_item_error,
    routine_progress,
    routine_step_finished,
    routine_step_started,
)

SEARCH_MATERIALIZED_VIEWS = [
    # Camada 1: Visões por fonte
    'mv_search_articles',
    'mv_search_books',
    'mv_search_patents',
    'mv_search_software',
    # Camada 2: Visão agregada consolidada
    'mv_researcher_search',
]

items_found = len(SEARCH_MATERIALIZED_VIEWS)
items_succeeded = 0
items_failed = 0


def _refresh_all_views(conn):
    global items_succeeded
    for idx, view_name in enumerate(SEARCH_MATERIALIZED_VIEWS, 1):
        msg = f'[Refresh MV] ({idx}/{items_found}) Atualizando {view_name}...'
        logger.info(msg)
        refresh_sql = f'REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name};'
        conn.execute(text(refresh_sql))
        items_succeeded += 1
        routine_progress(
            'refresh_search_views',
            idx,
            items_found,
            items_succeeded,
            items_failed,
        )


def refresh_views(engine=None):
    global items_found, items_succeeded, items_failed
    target_engine = engine or sync_engine
    items_found = len(SEARCH_MATERIALIZED_VIEWS)
    items_succeeded = 0
    items_failed = 0

    routine_step_started('refresh_search_views')

    try:
        # REFRESH CONCURRENTLY exige autocommit (fora de bloco de transação)
        with target_engine.connect().execution_options(
            isolation_level='AUTOCOMMIT'
        ) as conn:
            _refresh_all_views(conn)

        routine_step_finished(
            'refresh_search_views', total_processed=items_succeeded
        )
    except Exception as e:
        items_failed = items_found - items_succeeded
        err_msg = f'Erro ao atualizar visões materializadas: {e}'
        logger.error(err_msg)
        routine_item_error('materialized_views', str(e))
        raise e


def main():
    refresh_views()


if __name__ == '__main__':
    main()
