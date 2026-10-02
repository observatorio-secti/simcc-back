"""Repositório genérico de produções científicas canônicas v2.

Atende Livros, Capítulos de Livros, Softwares, Patentes e Eventos.
"""

from typing import Any, Mapping, Optional
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Table,
    and_,
    cast,
    func,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.schemas.params import PaginationParams
from simcc.v2.schemas.production import (
    ArticleMatch,
    ProductionBaseFilter,
    ProductionSort,
)


def search_tsquery(
    filters: ProductionBaseFilter,
) -> Optional[ColumnElement]:
    """Retorna o tsquery para busca textual ou None se q não foi informado."""
    if not filters.q or not filters.q.strip():
        return None
    return func.websearch_to_tsquery('pt_unaccent', filters.q.strip())


def build_production_conditions(
    table: Table,
    filters: ProductionBaseFilter,
) -> list[ColumnElement[bool]]:
    """Gera a lista de condições SQL para filtrar produções sobre a MV."""
    conds: list[ColumnElement[bool]] = []

    tsq = search_tsquery(filters)
    if tsq is not None:
        conds.append(table.c.search_vector.op('@@')(tsq))

    if filters.year_start is not None:
        conds.append(table.c.year >= filters.year_start)

    if filters.year_end is not None:
        conds.append(table.c.year <= filters.year_end)

    if filters.researcher_id:
        conds.append(
            table.c.researcher_ids.op('&&')(
                cast(filters.researcher_id, ARRAY(PG_UUID(as_uuid=True)))
            )
        )

    if filters.institution_id:
        conds.append(
            table.c.institution_ids.op('&&')(
                cast(filters.institution_id, ARRAY(PG_UUID(as_uuid=True)))
            )
        )

    if filters.graduate_program_id:
        conds.append(
            table.c.graduate_program_ids.op('&&')(
                cast(filters.graduate_program_id, ARRAY(PG_UUID(as_uuid=True)))
            )
        )

    return conds


def _order_clauses(
    table: Table,
    sort: ProductionSort,
    tsq: Optional[ColumnElement],
) -> list[ColumnElement]:
    """Define a ordenação dos registros."""
    clauses: list[ColumnElement] = []

    if sort.by == 'relevance' and tsq is not None:
        rank = func.ts_rank(table.c.search_vector, tsq)
        clauses.append(rank.desc() if sort.order == 'desc' else rank.asc())
        clauses.append(table.c.year.desc().nulls_last())
    elif sort.by == 'year':
        col = (
            table.c.year.desc().nulls_last()
            if sort.order == 'desc'
            else table.c.year.asc().nulls_last()
        )
        clauses.append(col)
    elif sort.by == 'title':
        col = (
            table.c.title.desc()
            if sort.order == 'desc'
            else table.c.title.asc()
        )
        clauses.append(col)
    else:
        clauses.append(table.c.year.desc().nulls_last())

    clauses.append(table.c.canonical_id)
    return clauses


async def count_production(
    session: AsyncSession,
    table: Table,
    filters: ProductionBaseFilter,
) -> int:
    """Conta total de registros para os filtros dados."""
    conds = build_production_conditions(table, filters)
    stmt = select(func.count()).select_from(table)
    if conds:
        stmt = stmt.where(and_(*conds))
    res = await session.execute(stmt)
    return res.scalar_one()


async def search_production(
    session: AsyncSession,
    table: Table,
    filters: ProductionBaseFilter,
    sort: ProductionSort,
    pagination: PaginationParams,
) -> list[Mapping[str, Any]]:
    """Consulta paginada de produções com filtros e ordenação."""
    conds = build_production_conditions(table, filters)
    tsq = search_tsquery(filters)
    stmt = select(table)
    if conds:
        stmt = stmt.where(and_(*conds))
    stmt = stmt.order_by(*_order_clauses(table, sort, tsq))
    stmt = stmt.limit(pagination.per_page).offset(
        (pagination.page - 1) * pagination.per_page
    )
    res = await session.execute(stmt)
    return res.mappings().all()


async def get_production_by_id(
    session: AsyncSession,
    table: Table,
    item_id: UUID | str,
    natural_key_col: Optional[str] = None,
) -> Optional[Mapping[str, Any]]:
    """Busca o registro por canonical_id, production_id ou natural key."""
    target_str = str(item_id).strip()
    try:
        uid = UUID(target_str)
        stmt = select(table).where(
            or_(
                table.c.canonical_id == uid,
                table.c.production_ids.op('@>')(
                    cast([uid], ARRAY(PG_UUID(as_uuid=True)))
                ),
            )
        )
    except ValueError:
        if natural_key_col and natural_key_col in table.c:
            col = table.c[natural_key_col]
            stmt = select(table).where(func.lower(col) == target_str.lower())
        else:
            return None

    res = await session.execute(stmt)
    return res.mappings().first()


async def get_production_snippets(
    session: AsyncSession,
    table: Table,
    canonical_ids: list[UUID],
    q: str,
    secondary_col: Optional[str] = None,
) -> dict[UUID, list[ArticleMatch]]:
    """Gera snippets com termos destacados para as produções da página."""
    if not canonical_ids or not q.strip():
        return {}

    tsq = func.websearch_to_tsquery('pt_unaccent', q.strip())
    select_cols = [
        table.c.canonical_id,
        func.ts_headline(
            'pt_unaccent',
            table.c.title,
            tsq,
            'StartSel=<b>, StopSel=</b>, HighlightAll=TRUE',
        ).label('title_hl'),
    ]

    has_secondary = secondary_col and secondary_col in table.c
    if has_secondary:
        select_cols.append(
            func.ts_headline(
                'pt_unaccent',
                func.coalesce(table.c[secondary_col], ''),
                tsq,
                'StartSel=<b>, StopSel=</b>, MaxWords=35, MinWords=15',
            ).label('sec_hl')
        )

    stmt = select(*select_cols).where(table.c.canonical_id.in_(canonical_ids))
    res = await session.execute(stmt)

    results: dict[UUID, list[ArticleMatch]] = {}
    for row in res.mappings().all():
        cid = row['canonical_id']
        matches: list[ArticleMatch] = []
        title_hl = row['title_hl'] or ''
        if '<b>' in title_hl:
            matches.append(ArticleMatch(field='title', snippet=title_hl))

        if has_secondary:
            sec_hl = row.get('sec_hl') or ''
            if '<b>' in sec_hl:
                matches.append(
                    ArticleMatch(field=secondary_col, snippet=sec_hl)
                )

        if matches:
            results[cid] = matches

    return results
