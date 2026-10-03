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

from simcc.core.db.models.expertise import GreatAreaExpertise
from simcc.core.db.models.researcher import ResearcherAreaExpertise
from simcc.v2.repositories.search_tables import mv_researcher_search
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


# Filtros de lista cujo nome é o da coluna na MV do tipo de produção
COLUMN_FILTERS = (
    'qualis',
    'category',
    'nature',
    'type_participation',
    'form_participation',
    'magazine_name',
    'issn',
)


def without_fields(
    filters: ProductionBaseFilter, fields: frozenset[str]
) -> ProductionBaseFilter:
    """Cópia do filtro com os campos indicados de volta ao valor padrão."""
    if not fields:
        return filters
    model_fields = type(filters).model_fields
    return filters.model_copy(
        update={
            field: model_fields[field].get_default(call_default_factory=True)
            for field in fields
        }
    )


def _uuid_array(values: list[UUID]) -> ColumnElement:
    return cast(values, ARRAY(PG_UUID(as_uuid=True)))


def _researchers_where(condition: ColumnElement[bool]) -> ColumnElement:
    """Array com os pesquisadores de `mv_researcher_search` que atendem a
    `condition`. Avaliado uma vez por consulta, mantém o uso do índice GIN
    de `researcher_ids`."""
    return (
        select(func.array_agg(mv_researcher_search.c.researcher_id))
        .where(condition)
        .scalar_subquery()
    )


def build_production_conditions(  # noqa: PLR0912
    table: Table,
    filters: ProductionBaseFilter,
    exclude: frozenset[str] = frozenset(),
) -> list[ColumnElement[bool]]:
    """Gera a lista de condições SQL para filtrar produções sobre a MV.

    `exclude` recebe nomes de campos do filtro a ignorar (faceting
    disjuntivo). Cidade e território vêm dos vínculos dos autores da
    plataforma, pela mesma fonte da busca de pesquisadores.
    """
    filters = without_fields(filters, exclude)
    conds: list[ColumnElement[bool]] = []

    tsq = search_tsquery(filters)
    if tsq is not None:
        conds.append(table.c.search_vector.op('@@')(tsq))

    if filters.year_start is not None:
        conds.append(table.c.year >= filters.year_start)

    if filters.year_end is not None:
        conds.append(table.c.year <= filters.year_end)

    for values, column in (
        (filters.researcher_id, table.c.researcher_ids),
        (filters.institution_id, table.c.institution_ids),
        (filters.graduate_program_id, table.c.graduate_program_ids),
    ):
        if values:
            conds.append(column.op('&&')(_uuid_array(values)))

    if filters.city_id:
        conds.append(
            table.c.researcher_ids.op('&&')(
                _researchers_where(
                    mv_researcher_search.c.city_ids.overlap(filters.city_id)
                )
            )
        )

    if filters.identity_territory:
        conds.append(
            table.c.researcher_ids.op('&&')(
                _researchers_where(
                    mv_researcher_search.c.identity_territories.overlap(
                        filters.identity_territory
                    )
                )
            )
        )

    if getattr(filters, 'area', None):
        rae = ResearcherAreaExpertise.__table__
        gae = GreatAreaExpertise.__table__
        normalized_areas = [a.replace(' ', '_').upper() for a in filters.area]
        area_cond = or_(
            gae.c.name.in_(filters.area),
            func.upper(gae.c.name).in_(normalized_areas),
        )
        conds.append(
            table.c.researcher_ids.op('&&')(
                _researchers_where(
                    mv_researcher_search.c.researcher_id.in_(
                        select(rae.c.researcher_id)
                        .select_from(
                            rae.join(
                                gae, gae.c.id == rae.c.great_area_expertise_id
                            )
                        )
                        .where(area_cond)
                    )
                )
            )
        )

    for field in COLUMN_FILTERS:
        values = getattr(filters, field, None)
        if values:
            conds.append(table.c[field].in_(values))

    has_open_access = getattr(filters, 'has_open_access', None)
    if has_open_access is not None:
        conds.append(table.c.has_open_access_pdf.is_(has_open_access))

    granted = getattr(filters, 'granted', None)
    if granted is True:
        conds.append(table.c.grant_date.isnot(None))
    elif granted is False:
        conds.append(table.c.grant_date.is_(None))

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
