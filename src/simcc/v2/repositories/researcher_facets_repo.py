"""Facets disjuntivos da busca de pesquisadores v2.

Todo facet segue o mesmo contrato (ver docs "Referência dos Facets"):
contagem de pesquisadores por valor, calculada com todos os filtros exceto
o do próprio facet; top `limit` por contagem com desempate estável; valores
selecionados sempre presentes; `total` de valores com resultado.

Para adicionar um facet: escreva uma função que monte os pares
(pesquisador, valor) e chame `rank_facet_values`, depois registre-a em
`FACET_BUILDERS` e em `ALLOWED_FACETS` (schemas/params.py).
"""

from collections.abc import Callable, Coroutine
from typing import Any, Optional

from sqlalchemy import ColumnElement, Select, String, func, null, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.expertise import GreatAreaExpertise
from simcc.core.db.models.graduate_program import GraduateProgram
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.location import City
from simcc.core.db.models.production import Foment
from simcc.core.db.models.researcher import ResearcherAreaExpertise
from simcc.v2.repositories.researcher_filters import (
    document_conditions,
    matching_researcher_ids,
    search_tsquery,
    without_fields,
)
from simcc.v2.repositories.search_tables import (
    mv_researcher_search,
    mv_search_documents,
)
from simcc.v2.schemas.filters import ResearcherFilter
from simcc.v2.schemas.researcher import FacetItem, FacetResult

r = mv_researcher_search
d = mv_search_documents


async def rank_facet_values(  # noqa: PLR0913
    session: AsyncSession,
    pairs: Select,
    *,
    selected: list[Any],
    limit: int,
    entity: Optional[type] = None,
    entity_id: Optional[ColumnElement] = None,
) -> FacetResult:
    """Conta itens por valor a partir de `pairs` e monta o `FacetResult`
    em uma consulta. `pairs` tem duas colunas: o id do item contado
    (pesquisador, produção...) e `value`.

    Com `entity`, os valores são ids: rótulo e sigla vêm da tabela da
    entidade, e selecionados sem resultado entram via LEFT JOIN. Sem ela, o
    próprio valor é o rótulo, e selecionados sem resultado são completados
    sem consulta extra.
    """
    pairs_sq = pairs.subquery()
    counts = (
        select(
            pairs_sq.c.value,
            func.count(func.distinct(pairs_sq.c[0])).label('n'),
        )
        .group_by(pairs_sq.c.value)
        .subquery()
    )

    if entity is not None:
        acronym = getattr(entity, 'acronym', None)
        has_results = counts.c.value.isnot(None)
        source = (
            select(
                entity_id.label('value'),
                entity.name.label('label'),
                (
                    acronym if acronym is not None else null().cast(String)
                ).label('acronym'),
                func.coalesce(counts.c.n, 0).label('n'),
                counts.c.value.label('counted'),
            )
            .select_from(entity)
            .outerjoin(counts, counts.c.value == entity_id)
            .where(
                or_(has_results, entity_id.in_(selected))
                if selected
                else has_results
            )
        )
    else:
        source = select(
            counts.c.value,
            counts.c.value.cast(String).label('label'),
            null().cast(String).label('acronym'),
            counts.c.n,
            counts.c.value.label('counted'),
        )
    source = source.subquery()

    ranked = select(
        source,
        func
        .row_number()
        .over(
            order_by=(
                source.c.n.desc(),
                source.c.label.asc(),
                source.c.value.asc(),
            )
        )
        .label('position'),
        # Só valores com resultado entram no total
        func.count(source.c.counted).over().label('total'),
    ).subquery()

    keep = ranked.c.position <= limit
    if selected:
        keep = or_(keep, ranked.c.value.in_(selected))
    rows = (
        (
            await session.execute(
                select(ranked).where(keep).order_by(ranked.c.position)
            )
        )
        .mappings()
        .all()
    )

    selected_keys = {str(v) for v in selected}
    items = [
        FacetItem(
            value=str(row['value']),
            label=row['label'],
            acronym=row['acronym'],
            count=row['n'],
            selected=str(row['value']) in selected_keys,
        )
        for row in rows
    ]
    if entity is None:
        present = {item.value for item in items}
        items += [
            FacetItem(value=key, label=key, count=0, selected=True)
            for key in (str(v) for v in selected)
            if key not in present
        ]
    return FacetResult(total=rows[0]['total'] if rows else 0, items=items)


def _array_pairs(
    filters: ResearcherFilter, field: str, array_column: ColumnElement
) -> Select:
    return select(
        r.c.researcher_id, func.unnest(array_column).label('value')
    ).where(
        r.c.researcher_id.in_(
            matching_researcher_ids(filters, exclude=frozenset({field}))
        )
    )


def _column_pairs(
    filters: ResearcherFilter, field: str, column: ColumnElement
) -> Select:
    return select(r.c.researcher_id, column.label('value')).where(
        column.isnot(None),
        r.c.researcher_id.in_(
            matching_researcher_ids(filters, exclude=frozenset({field}))
        ),
    )


async def fetch_institution_facet(session, filters, limit=20):
    return await rank_facet_values(
        session,
        _array_pairs(filters, 'institution_id', r.c.institution_ids),
        selected=filters.institution_id,
        limit=limit,
        entity=Institution,
        entity_id=Institution.id,
    )


async def fetch_graduate_program_facet(session, filters, limit=20):
    return await rank_facet_values(
        session,
        _array_pairs(filters, 'graduate_program_id', r.c.graduate_program_ids),
        selected=filters.graduate_program_id,
        limit=limit,
        entity=GraduateProgram,
        entity_id=GraduateProgram.graduate_program_id,
    )


async def fetch_city_facet(session, filters, limit=20):
    return await rank_facet_values(
        session,
        _array_pairs(filters, 'city_id', r.c.city_ids),
        selected=filters.city_id,
        limit=limit,
        entity=City,
        entity_id=City.id,
    )


async def fetch_identity_territory_facet(session, filters, limit=20):
    return await rank_facet_values(
        session,
        _array_pairs(filters, 'identity_territory', r.c.identity_territories),
        selected=filters.identity_territory,
        limit=limit,
    )


async def fetch_graduation_facet(session, filters, limit=20):
    return await rank_facet_values(
        session,
        _column_pairs(filters, 'graduation', r.c.graduation),
        selected=filters.graduation,
        limit=limit,
    )


async def fetch_classification_facet(session, filters, limit=20):
    return await rank_facet_values(
        session,
        _column_pairs(filters, 'classification', r.c.classification),
        selected=filters.classification,
        limit=limit,
    )


async def fetch_source_type_facet(session, filters, limit=20):
    """Pesquisadores por tipo de obra que conta para a busca (casa com `q`
    e está no intervalo de anos). Funciona com ou sem `q`."""
    exclude = frozenset({'source_type'})
    unfiltered = without_fields(filters, exclude)
    pairs = select(d.c.researcher_id, d.c.source_type.label('value')).where(
        d.c.researcher_id.in_(matching_researcher_ids(filters, exclude)),
        *document_conditions(unfiltered),
    )
    return await rank_facet_values(
        session, pairs, selected=filters.source_type, limit=limit
    )


async def fetch_year_facet(session, filters, limit=20):
    """Histograma de anos, do ano com mais pesquisadores para o com menos
    (desempate: ano mais recente primeiro).

    Com `q` ou `source_type`, conta os anos das obras que contam para a
    busca; sem eles, os anos de qualquer produção do pesquisador.
    """
    exclude = frozenset({'year_start', 'year_end'})
    matching = matching_researcher_ids(filters, exclude)
    if search_tsquery(filters) is not None or filters.source_type:
        unfiltered = without_fields(filters, exclude)
        pairs = select(d.c.researcher_id, d.c.year_.label('year')).where(
            d.c.researcher_id.in_(matching),
            d.c.year_.isnot(None),
            *document_conditions(unfiltered),
        )
    else:
        pairs = select(
            r.c.researcher_id,
            func.unnest(r.c.production_years).label('year'),
        ).where(r.c.researcher_id.in_(matching))
    unnested = pairs.subquery()

    n = func.count(func.distinct(unnested.c.researcher_id))
    rows = (
        (
            await session.execute(
                select(
                    unnested.c.year,
                    n.label('n'),
                    func.count().over().label('total'),
                )
                .group_by(unnested.c.year)
                .order_by(n.desc(), unnested.c.year.desc())
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


async def fetch_area_facet(session, filters, limit=20):
    """Contagem de pesquisadores por grande área do conhecimento."""
    exclude = frozenset({'area'})
    rae = ResearcherAreaExpertise.__table__
    gae = GreatAreaExpertise.__table__
    pairs = (
        select(rae.c.researcher_id, gae.c.name.label('value'))
        .select_from(rae.join(gae, gae.c.id == rae.c.great_area_expertise_id))
        .where(
            gae.c.name.isnot(None),
            rae.c.researcher_id.in_(
                matching_researcher_ids(filters, exclude=exclude)
            ),
        )
    )
    return await rank_facet_values(
        session, pairs, selected=filters.area, limit=limit
    )


async def fetch_modality_facet(session, filters, limit=20):
    """Contagem de pesquisadores por modalidade de bolsa/fomento."""
    exclude = frozenset({'modality'})
    f = Foment.__table__
    pairs = (
        select(f.c.researcher_id, f.c.modality_name.label('value'))
        .select_from(f)
        .where(
            f.c.modality_name.isnot(None),
            f.c.researcher_id.in_(
                matching_researcher_ids(filters, exclude=exclude)
            ),
        )
    )
    return await rank_facet_values(
        session, pairs, selected=filters.modality, limit=limit
    )


FacetBuilder = Callable[
    [AsyncSession, ResearcherFilter, int], Coroutine[Any, Any, FacetResult]
]

FACET_BUILDERS: dict[str, FacetBuilder] = {
    'institution': fetch_institution_facet,
    'graduate_program': fetch_graduate_program_facet,
    'city': fetch_city_facet,
    'identity_territory': fetch_identity_territory_facet,
    'graduation': fetch_graduation_facet,
    'classification': fetch_classification_facet,
    'year': fetch_year_facet,
    'source_type': fetch_source_type_facet,
    'area': fetch_area_facet,
    'modality': fetch_modality_facet,
}


async def fetch_requested_facets(
    session: AsyncSession,
    filters: ResearcherFilter,
    requested_facets: list[str],
    limit: int = 20,
) -> dict[str, FacetResult]:
    """Calcula os facets pedidos, um por consulta."""
    return {
        name: await FACET_BUILDERS[name](session, filters, limit)
        for name in requested_facets
    }
