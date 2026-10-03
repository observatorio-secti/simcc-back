"""Facets disjuntivos das listagens de produção v2.

Segue o mesmo contrato dos facets de pesquisadores (ver docs "Referência
dos Facets"), contando produções em vez de pesquisadores: cada facet é
calculado com todos os filtros exceto o do próprio campo.

Para adicionar um facet de coluna: declare o filtro de lista no schema do
tipo de produção, com o mesmo nome da coluna na MV, e registre o nome em
`COLUMN_FILTERS` (production_repo.py). Ele passa a valer como filtro e
como facet.
"""

from sqlalchemy import Select, Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.expertise import GreatAreaExpertise
from simcc.core.db.models.graduate_program import GraduateProgram
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.location import City
from simcc.core.db.models.researcher import ResearcherAreaExpertise
from simcc.v2.repositories.production_repo import (
    COLUMN_FILTERS,
    build_production_conditions,
)
from simcc.v2.repositories.researcher_facets_repo import rank_facet_values
from simcc.v2.repositories.search_tables import mv_researcher_search
from simcc.v2.schemas.production import (
    COMMON_PRODUCTION_FACETS,
    ProductionBaseFilter,
)
from simcc.v2.schemas.researcher import FacetItem, FacetResult

r = mv_researcher_search


def allowed_facets(filters: ProductionBaseFilter) -> list[str]:
    """Facets aceitos pelo tipo de produção do filtro."""
    fields = type(filters).model_fields
    return [
        *COMMON_PRODUCTION_FACETS,
        *(field for field in COLUMN_FILTERS if field in fields),
    ]


def _array_pairs(table: Table, filters, field: str, column) -> Select:
    return select(
        table.c.canonical_id, func.unnest(column).label('value')
    ).where(*build_production_conditions(table, filters, frozenset({field})))


def _researcher_pairs(table: Table, filters, field: str, column) -> Select:
    """Pares (produção, valor) de um atributo dos autores da plataforma."""
    authors = (
        select(
            table.c.canonical_id,
            func.unnest(table.c.researcher_ids).label('researcher_id'),
        )
        .where(
            *build_production_conditions(table, filters, frozenset({field}))
        )
        .subquery()
    )
    return select(
        authors.c.canonical_id, func.unnest(column).label('value')
    ).join(r, r.c.researcher_id == authors.c.researcher_id)


async def _institution_facet(session, table, filters, limit):
    return await rank_facet_values(
        session,
        _array_pairs(
            table, filters, 'institution_id', table.c.institution_ids
        ),
        selected=filters.institution_id,
        limit=limit,
        entity=Institution,
        entity_id=Institution.id,
    )


async def _graduate_program_facet(session, table, filters, limit):
    return await rank_facet_values(
        session,
        _array_pairs(
            table,
            filters,
            'graduate_program_id',
            table.c.graduate_program_ids,
        ),
        selected=filters.graduate_program_id,
        limit=limit,
        entity=GraduateProgram,
        entity_id=GraduateProgram.graduate_program_id,
    )


async def _city_facet(session, table, filters, limit):
    return await rank_facet_values(
        session,
        _researcher_pairs(table, filters, 'city_id', r.c.city_ids),
        selected=filters.city_id,
        limit=limit,
        entity=City,
        entity_id=City.id,
    )


async def _identity_territory_facet(session, table, filters, limit):
    return await rank_facet_values(
        session,
        _researcher_pairs(
            table, filters, 'identity_territory', r.c.identity_territories
        ),
        selected=filters.identity_territory,
        limit=limit,
    )


async def _column_facet(session, table, filters, limit, field: str):
    column = table.c[field]
    pairs = select(table.c.canonical_id, column.label('value')).where(
        column.isnot(None),
        column != '',  # noqa: PLC1901
        *build_production_conditions(table, filters, frozenset({field})),
    )
    return await rank_facet_values(
        session, pairs, selected=getattr(filters, field), limit=limit
    )


async def _year_facet(session, table, filters, limit):
    """Histograma de anos, do ano com mais produções para o com menos
    (desempate: ano mais recente primeiro)."""
    n = func.count()
    rows = (
        (
            await session.execute(
                select(
                    table.c.year,
                    n.label('n'),
                    func.count().over().label('total'),
                )
                .where(
                    table.c.year.isnot(None),
                    *build_production_conditions(
                        table, filters, frozenset({'year_start', 'year_end'})
                    ),
                )
                .group_by(table.c.year)
                .order_by(n.desc(), table.c.year.desc())
                .limit(limit)
            )
        )
        .mappings()
        .all()
    )
    return FacetResult(
        total=rows[0]['total'] if rows else 0,
        items=[
            FacetItem(
                value=str(row['year']),
                label=str(row['year']),
                count=row['n'],
            )
            for row in rows
        ],
    )


async def _area_facet(session, table, filters, limit):
    rae = ResearcherAreaExpertise.__table__
    gae = GreatAreaExpertise.__table__
    authors = (
        select(
            table.c.canonical_id,
            func.unnest(table.c.researcher_ids).label('researcher_id'),
        )
        .where(
            *build_production_conditions(table, filters, frozenset({'area'}))
        )
        .subquery()
    )
    pairs = (
        select(authors.c.canonical_id, gae.c.name.label('value'))
        .join(rae, rae.c.researcher_id == authors.c.researcher_id)
        .join(gae, gae.c.id == rae.c.great_area_expertise_id)
        .where(gae.c.name.isnot(None))
    )
    return await rank_facet_values(
        session,
        pairs,
        selected=filters.area,
        limit=limit,
    )


_COMMON_BUILDERS = {
    'institution': _institution_facet,
    'graduate_program': _graduate_program_facet,
    'city': _city_facet,
    'identity_territory': _identity_territory_facet,
    'year': _year_facet,
    'area': _area_facet,
}


async def fetch_requested_facets(
    session: AsyncSession,
    table: Table,
    filters: ProductionBaseFilter,
    requested_facets: list[str],
    limit: int = 20,
) -> dict[str, FacetResult]:
    """Calcula os facets pedidos, um por consulta."""
    facets = {}
    for name in requested_facets:
        if name in _COMMON_BUILDERS:
            facets[name] = await _COMMON_BUILDERS[name](
                session, table, filters, limit
            )
        else:
            facets[name] = await _column_facet(
                session, table, filters, limit, name
            )
    return facets
