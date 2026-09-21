# ruff: noqa: PLR2004
import asyncio

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

SEARCH_MATERIALIZED_VIEWS = [
    'mv_search_articles',
    'mv_search_books',
    'mv_search_patents',
    'mv_search_software',
    'mv_researcher_search',
]

CURRENT_HEAD_REVISION = 'e7796887be76'
PARENT_REVISION = '9b38fbff8df4'


def get_alembic_config() -> Config:
    """Retorna configuração do Alembic apontando para alembic.ini."""
    return Config('alembic.ini')


@pytest.mark.integration
def test_alembic_single_head():
    """Garante que a árvore possui exatamente um único head."""
    cfg = get_alembic_config()
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()

    assert len(heads) == 1, (
        f'Esperado 1 head no Alembic, encontrado {len(heads)}: {heads}'
    )
    assert heads[0] == CURRENT_HEAD_REVISION


@pytest.mark.integration
def test_alembic_revisions_chain_integrity():
    """Valida integridade da cadeia (sem elos órfãos ou quebrados)."""
    cfg = get_alembic_config()
    script = ScriptDirectory.from_config(cfg)
    revisions = list(script.walk_revisions(base='base', head='head'))

    assert len(revisions) > 0, 'Nenhuma revisão encontrada no Alembic.'

    rev_map = {r.revision: r for r in revisions}
    for rev in revisions:
        if rev.down_revision:
            if isinstance(rev.down_revision, tuple):
                for parent_rev in rev.down_revision:
                    assert parent_rev in rev_map, (
                        f'Rev {rev.revision} -> '
                        f'parent inexistente {parent_rev}'
                    )
            else:
                assert rev.down_revision in rev_map, (
                    f'Rev {rev.revision} -> '
                    f'parent inexistente {rev.down_revision}'
                )


@pytest.mark.integration
def test_alembic_step_by_step_plan():
    """Valida a ordenação sequencial para execução passo a passo."""
    cfg = get_alembic_config()
    script = ScriptDirectory.from_config(cfg)
    ordered_revs = list(reversed(list(script.walk_revisions('base', 'head'))))

    assert len(ordered_revs) > 0
    assert ordered_revs[-1].revision == CURRENT_HEAD_REVISION


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_materialized_views_lifecycle_and_concurrent_refresh(
    session,
):
    """Testa ciclo completo de downgrade, upgrade e REFRESH CONCURRENTLY."""
    cfg = get_alembic_config()

    check_table = await session.execute(
        text("SELECT to_regclass('alembic_version');")
    )
    if check_table.scalar() is not None:
        check_ver = await session.execute(
            text('SELECT version_num FROM alembic_version LIMIT 1;')
        )
        current_ver = check_ver.scalar()
    else:
        current_ver = None

    if current_ver is None:
        await asyncio.to_thread(command.stamp, cfg, PARENT_REVISION)
    elif current_ver == CURRENT_HEAD_REVISION:
        await asyncio.to_thread(command.downgrade, cfg, PARENT_REVISION)

    await session.rollback()

    # 1. Upgrade para CURRENT_HEAD_REVISION
    await asyncio.to_thread(command.upgrade, cfg, CURRENT_HEAD_REVISION)
    await session.rollback()

    # 2. Verifica se todas as MVs foram criadas
    query_mvs = (
        "SELECT matviewname FROM pg_matviews WHERE matviewname LIKE 'mv_%';"
    )
    res_up = await session.execute(text(query_mvs))
    existing_mvs_up = {row[0] for row in res_up.fetchall()}
    for mv in SEARCH_MATERIALIZED_VIEWS:
        assert mv in existing_mvs_up, (
            f'Visão {mv} não encontrada no banco após upgrade!'
        )

    # 3. Testa downgrade de volta para PARENT_REVISION
    await asyncio.to_thread(command.downgrade, cfg, PARENT_REVISION)
    await session.rollback()
    res_down = await session.execute(text(query_mvs))
    existing_mvs_down = {row[0] for row in res_down.fetchall()}
    for mv in SEARCH_MATERIALIZED_VIEWS:
        assert mv not in existing_mvs_down, (
            f'Visão {mv} ainda existe após downgrade!'
        )

    # 4. Upgrade de volta para HEAD para deixar o ambiente íntegro
    await asyncio.to_thread(command.upgrade, cfg, CURRENT_HEAD_REVISION)
    await session.rollback()

    # 5. Testa REFRESH CONCURRENTLY na ordem (Camada 1 -> Camada 2)
    layer1_views = [
        'mv_search_articles',
        'mv_search_books',
        'mv_search_patents',
        'mv_search_software',
    ]
    for mv in layer1_views:
        await session.execute(
            text(f'REFRESH MATERIALIZED VIEW CONCURRENTLY {mv};')
        )

    await session.execute(
        text('REFRESH MATERIALIZED VIEW CONCURRENTLY mv_researcher_search;')
    )
