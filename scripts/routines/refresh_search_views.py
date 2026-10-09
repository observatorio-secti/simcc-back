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
from simcc.core.settings import Settings
from simcc.v2.services.mv_refresh_service import SEARCH_MATERIALIZED_VIEWS
from simcc.v2.services.search_cache import bump_search_generation

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


def _invalidate_search_cache():
    settings = Settings()
    if not settings.REDIS_ENABLED:
        return
    generation = bump_search_generation(settings.REDIS_URL)
    if generation is not None:
        logger.info(
            f'[Refresh MV] Cache de busca v2 invalidado (geração {generation})'
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

        _invalidate_search_cache()

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
