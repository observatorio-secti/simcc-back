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

from sqlalchemy import (
    ColumnElement,
    Integer,
    Select,
    String,
    func,
    literal,
    null,
    or_,
    select,
    union_all,
)
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.expertise import GreatAreaExpertise
from simcc.core.db.models.graduate_program import GraduateProgram
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.location import City, IdentityTerritory, Municipality
from simcc.core.db.models.production import Foment
from simcc.core.db.models.researcher import ResearcherAreaExpertise
from simcc.core.db.models.researcher_institution import ResearcherInstitution
from simcc.v2.repositories.geo import (
    NO_TERRITORY_LABEL,
    resolve_territory_codes,
)
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
from simcc.v2.schemas.kinds import from_db, to_db
from simcc.v2.schemas.params import facet_param
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
    code: Optional[ColumnElement] = None,
) -> FacetResult:
    """Conta itens por valor a partir de `pairs` e monta o `FacetResult`
    em uma consulta. `pairs` tem duas colunas: o id do item contado
    (pesquisador, produção...) e `value`.

    Com `entity`, os valores são ids: rótulo e sigla vêm da tabela da
    entidade, e selecionados sem resultado entram via LEFT JOIN. Sem ela, o
    próprio valor é o rótulo, e selecionados sem resultado são completados
    sem consulta extra. `code` é a coluna da entidade com o código estável
    (SEI, IBGE), quando houver.

    `covered` é a quantidade de itens distintos com algum valor.
    """
    pairs_sq = pairs.cte('facet_pairs')
    covered = select(
        func.count(func.distinct(pairs_sq.c[0]))
    ).scalar_subquery()
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
                (code if code is not None else null().cast(Integer)).label(
                    'code'
                ),
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
            null().cast(Integer).label('code'),
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
        covered.label('covered'),
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
            code=int(row['code']) if row['code'] is not None else None,
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
    return FacetResult(
        total=rows[0]['total'] if rows else 0,
        covered=rows[0]['covered'] if rows else 0,
        items=items,
    )


# Campos de filtro que cada faceta ignora, quando são mais de um
_FACET_EXCLUDES = {'city_id': frozenset({'city_id', 'city_code'})}


def _array_pairs(
    filters: ResearcherFilter, field: str, array_column: ColumnElement
) -> Select:
    exclude = _FACET_EXCLUDES.get(field, frozenset({field}))
    return select(
        r.c.researcher_id, func.unnest(array_column).label('value')
    ).where(r.c.researcher_id.in_(matching_researcher_ids(filters, exclude)))


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
        code=City.ibge_code,
    )


async def fetch_identity_territory_facet(session, filters, limit=20):
    """Pesquisadores por território, com `value` e `code` = código SEI."""
    return await rank_facet_values(
        session,
        _array_pairs(filters, 'identity_territory', r.c.territory_codes),
        selected=await resolve_territory_codes(
            session, filters.identity_territory
        ),
        limit=limit,
        entity=IdentityTerritory,
        entity_id=IdentityTerritory.code,
        code=IdentityTerritory.code,
    )


# =========================================================================
# Faceta hierárquica território → município
# =========================================================================

IT = IdentityTerritory
M = Municipality
RI = ResearcherInstitution

# Filtros ignorados pela faceta territory_city: selecionar um território ou
# município não esvazia os demais.
TERRITORY_CITY_EXCLUDE = frozenset({
    'identity_territory',
    'city_id',
    'city_code',
})


def researcher_geo_pairs(source) -> Select:
    """Pares (item, território, município) por vínculo, a partir de uma
    subconsulta com `item_id` e `researcher_id`. Cada vínculo traz cidade e
    território juntos, sem cruzar vínculos diferentes do pesquisador."""
    return select(
        source.c.item_id,
        M.territory_code.label('parent'),
        M.ibge_code.label('child'),
    ).select_from(
        source
        .join(RI, RI.researcher_id == source.c.researcher_id)
        .join(City, City.id == RI.city_id)
        .join(M, M.ibge_code == City.ibge_code)
    )


async def _missing_labels(
    session: AsyncSession, parents: set[int], children: set[str]
) -> tuple[dict[int, str], dict[str, tuple[str, Optional[int]]]]:
    """Rótulos de selecionados sem resultado: território por código e
    (nome, território) por município. Inclui os territórios dos municípios."""
    child_info: dict[str, tuple[str, Optional[int]]] = {}
    if children:
        rows = await session.execute(
            select(M.ibge_code, M.name, M.territory_code).where(
                M.ibge_code.in_(children)
            )
        )
        child_info = {
            code: (name, None if parent is None else int(parent))
            for code, name, parent in rows
        }
    wanted = parents | {p for _, p in child_info.values() if p is not None}
    parent_labels: dict[int, str] = {}
    if wanted:
        rows = await session.execute(
            select(IT.code, IT.name).where(IT.code.in_(wanted))
        )
        parent_labels = {int(code): name for code, name in rows}
    return parent_labels, child_info


def _territory_item(parent, label, count, selected) -> FacetItem:
    return FacetItem(
        value=None if parent is None else str(parent),
        code=None if parent is None else int(parent),
        label=label,
        count=count,
        selected=selected,
        children=[],
    )


async def rank_pivot_values(  # noqa: C901, PLR0912, PLR0914
    session: AsyncSession,
    pairs: Select,
    *,
    selected_parents: list[int],
    selected_children: list[str],
    limit: int,
) -> FacetResult:
    """Faceta hierárquica território → município em uma consulta.

    `pairs` tem três colunas: o id do item contado, `parent` (código SEI,
    nulo fora da BA) e `child` (código IBGE). O `limit` vale por nível: até
    `limit` territórios e até `limit` municípios em cada um. A contagem de
    cada nível é de itens distintos, então o território não é a soma dos
    filhos. O grupo sem território vem por último.
    """
    p = pairs.cte('pivot_pairs')
    covered = select(func.count(func.distinct(p.c[0]))).scalar_subquery()

    parent_counts = (
        select(p.c.parent, func.count(func.distinct(p.c[0])).label('n'))
        .group_by(p.c.parent)
        .subquery()
    )
    parent_label = func.coalesce(IT.name, NO_TERRITORY_LABEL)
    parents = select(
        literal('p').label('kind'),
        parent_counts.c.parent,
        null().cast(String).label('child'),
        parent_label.label('label'),
        parent_counts.c.n,
        func
        .row_number()
        .over(
            order_by=(
                parent_counts.c.parent.is_(None),
                parent_counts.c.n.desc(),
                parent_label.asc(),
                parent_counts.c.parent.asc(),
            )
        )
        .label('position'),
        func.count().over().label('total'),
    ).select_from(
        parent_counts.outerjoin(IT, IT.code == parent_counts.c.parent)
    )

    child_counts = (
        select(
            p.c.parent,
            p.c.child,
            func.count(func.distinct(p.c[0])).label('n'),
        )
        .group_by(p.c.parent, p.c.child)
        .subquery()
    )
    children = select(
        literal('c').label('kind'),
        child_counts.c.parent,
        child_counts.c.child.cast(String).label('child'),
        M.name.label('label'),
        child_counts.c.n,
        func
        .row_number()
        .over(
            partition_by=child_counts.c.parent,
            order_by=(
                child_counts.c.n.desc(),
                M.name.asc(),
                child_counts.c.child.asc(),
            ),
        )
        .label('position'),
        func.count().over(partition_by=child_counts.c.parent).label('total'),
    ).select_from(child_counts.join(M, M.ibge_code == child_counts.c.child))

    ranked = union_all(parents, children).subquery()
    keep = ranked.c.position <= limit
    if selected_parents:
        keep = or_(
            keep,
            (ranked.c.kind == 'p') & ranked.c.parent.in_(selected_parents),
        )
    if selected_children:
        keep = or_(
            keep,
            (ranked.c.kind == 'c') & ranked.c.child.in_(selected_children),
        )
    rows = (
        (
            await session.execute(
                select(ranked, covered.label('covered'))
                .where(keep)
                .order_by(ranked.c.kind.desc(), ranked.c.position)
            )
        )
        .mappings()
        .all()
    )

    sel_parents = {int(v) for v in selected_parents}
    sel_children = {str(v).strip() for v in selected_children}
    territories: dict[Optional[int], FacetItem] = {}
    total = 0
    pending_children = []
    for row in rows:
        parent = None if row['parent'] is None else int(row['parent'])
        if row['kind'] == 'p':
            total = row['total']
            territories[parent] = _territory_item(
                parent, row['label'], row['n'], parent in sel_parents
            )
        else:
            pending_children.append((parent, row))
    for parent, row in pending_children:
        territory = territories.get(parent)
        if territory is None:
            continue
        territory.children.append(
            FacetItem(
                value=row['child'],
                code=int(row['child']),
                label=row['label'],
                count=row['n'],
                selected=row['child'] in sel_children,
            )
        )

    # Selecionados sem resultado entram com contagem zero
    present_children = {
        child.value for t in territories.values() for child in t.children
    }
    missing_parents = sel_parents - set(territories)
    missing_children = sel_children - present_children
    if missing_parents or missing_children:
        parent_labels, child_info = await _missing_labels(
            session, missing_parents, missing_children
        )
        for code in sorted(missing_parents):
            if code in parent_labels:
                territories[code] = _territory_item(
                    code, parent_labels[code], 0, True
                )
        for code, (name, parent) in sorted(child_info.items()):
            if parent not in territories:
                label = parent_labels.get(parent, NO_TERRITORY_LABEL)
                territories[parent] = _territory_item(
                    parent, label, 0, parent in sel_parents
                )
            territories[parent].children.append(
                FacetItem(
                    value=code,
                    code=int(code),
                    label=name,
                    count=0,
                    selected=True,
                )
            )

    items = sorted(
        territories.values(),
        key=lambda t: (t.value is None, -t.count, t.label, t.code or 0),
    )
    return FacetResult(
        total=total,
        covered=rows[0]['covered'] if rows else 0,
        items=items,
    )


async def fetch_territory_city_facet(session, filters, limit=20):
    """Pesquisadores por território e município do vínculo."""
    matching = matching_researcher_ids(
        filters, exclude=TERRITORY_CITY_EXCLUDE
    ).subquery()
    source = select(
        matching.c.researcher_id.label('item_id'),
        matching.c.researcher_id,
    ).subquery()
    return await rank_pivot_values(
        session,
        researcher_geo_pairs(source),
        selected_parents=await resolve_territory_codes(
            session, filters.identity_territory
        ),
        selected_children=filters.city_code,
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
    facet = await rank_facet_values(
        session,
        pairs,
        selected=[to_db(t) for t in filters.source_type],
        limit=limit,
    )
    for item in facet.items:
        item.value = item.label = from_db(item.value)
    return facet


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
    'territory_city': fetch_territory_city_facet,
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
    facets = {}
    for name in requested_facets:
        facet = await FACET_BUILDERS[name](session, filters, limit)
        facet.param = facet_param(name)
        facets[name] = facet
    return facets
