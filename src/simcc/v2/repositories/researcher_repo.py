"""Repositório de acesso a dados para pesquisadores v2 sobre MVs."""

from collections.abc import Sequence
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Float,
    RowMapping,
    Select,
    and_,
    cast,
    false,
    func,
    literal_column,
    or_,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from simcc.core.db.models.graduate_program import (
    GraduateProgram as GraduateProgramDB,
)
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.location import City
from simcc.core.db.models.researcher_institution import ResearcherInstitution
from simcc.v2.repositories.researcher_filters import (
    build_researcher_conditions,
)
from simcc.v2.repositories.search_tables import (
    mv_researcher_search,
    mv_search_documents,
)
from simcc.v2.schemas.city import CityRef
from simcc.v2.schemas.filters import ResearcherFilter
from simcc.v2.schemas.institution import InstitutionRef
from simcc.v2.schemas.params import PaginationParams, SortParams
from simcc.v2.schemas.researcher import (
    Affiliation,
    FacetItem,
    FacetResult,
    MatchesSummary,
    MatchItem,
    ResearcherCounts,
    ResearcherSummary,
    researcher_image_url,
)

SORTABLE = {
    'name': mv_researcher_search.c.name,
    'id': mv_researcher_search.c.researcher_id,
}


def _apply_sorting(
    stmt: Select,
    sort: SortParams,
    filters: ResearcherFilter,
) -> Select:
    """Aplica ordenação determinística ou por relevância."""
    r = mv_researcher_search
    if sort.sort_by == 'relevance' and filters.q and filters.q.strip():
        clean_q = filters.q.strip()
        tsq = func.websearch_to_tsquery('pt_unaccent', clean_q)
        profile_rank = func.ts_rank(r.c.profile_vector, tsq)

        d = mv_search_documents
        doc_conds = [
            d.c.researcher_id == r.c.researcher_id,
            d.c.search_vector.op('@@')(tsq),
        ]
        if filters.year_start is not None:
            doc_conds.append(d.c.year_ >= filters.year_start)
        if filters.year_end is not None:
            doc_conds.append(d.c.year_ <= filters.year_end)

        doc_relevance = (
            select(
                func.coalesce(
                    func.max(func.ts_rank(d.c.search_vector, tsq)), 0.0
                )
                + func.ln(
                    func.coalesce(cast(func.count(d.c.source_id), Float), 0.0)
                    + 1.0
                )
            )
            .where(and_(*doc_conds))
            .scalar_subquery()
        )

        relevance_score = (profile_rank * 1.5) + doc_relevance
        if sort.sort_order == 'desc':
            return stmt.order_by(
                relevance_score.desc(),
                r.c.name.asc(),
                r.c.researcher_id.asc(),
            )
        return stmt.order_by(
            relevance_score.asc(),
            r.c.name.asc(),
            r.c.researcher_id.asc(),
        )

    sort_col = SORTABLE.get(sort.sort_by, r.c.name)
    if sort.sort_order == 'desc':
        return (
            stmt.order_by(sort_col.desc())
            if sort_col is r.c.researcher_id
            else stmt.order_by(sort_col.desc(), r.c.researcher_id.desc())
        )

    return (
        stmt.order_by(sort_col.asc())
        if sort_col is r.c.researcher_id
        else stmt.order_by(sort_col.asc(), r.c.researcher_id.asc())
    )


async def fetch_researchers(
    session: AsyncSession,
    filters: ResearcherFilter,
    pagination: PaginationParams,
    sort: SortParams,
) -> tuple[list[ResearcherSummary], int]:
    """Consulta pesquisadores aplicando filtros, ordenação e paginação."""
    conditions = build_researcher_conditions(filters)
    r = mv_researcher_search

    # 1. Total de itens
    count_stmt = select(func.count(r.c.researcher_id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total_items = (await session.execute(count_stmt)).scalar() or 0

    if total_items == 0:
        return [], 0

    # 2. Registros da página
    stmt = select(
        r.c.researcher_id,
        r.c.name,
        r.c.graduation,
        r.c.classification,
        r.c.lattes_update,
        *(r.c[field] for field in ResearcherCounts.model_fields),
    )
    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = _apply_sorting(stmt, sort, filters)

    offset = max(0, (pagination.page - 1) * pagination.per_page)
    stmt = stmt.offset(offset).limit(pagination.per_page)

    result = await session.execute(stmt)
    rows = result.mappings().all()
    data = [
        ResearcherSummary(
            researcher_id=row['researcher_id'],
            name=row['name'],
            image=researcher_image_url(row['researcher_id']),
            graduation=row['graduation'],
            classification=row['classification'],
            lattes_update=row['lattes_update'],
            counts=ResearcherCounts.model_validate(dict(row)),
        )
        for row in rows
    ]

    return data, total_items


async def fetch_affiliations(
    session: AsyncSession,
    page_ids: list[UUID],
) -> dict[UUID, list[Affiliation]]:
    """Busca os vínculos institucionais dos pesquisadores da página."""
    if not page_ids:
        return {}

    ri = ResearcherInstitution
    stmt = (
        select(
            ri.researcher_id,
            ri.workload,
            ri.identity_territory,
            Institution.id,
            Institution.name,
            Institution.acronym,
            Institution.image,
            City.id.label('city_id'),
            City.name.label('city_name'),
        )
        .join(Institution, Institution.id == ri.institution_id)
        .outerjoin(City, City.id == ri.city_id)
        .where(ri.researcher_id.in_(page_ids))
        .order_by(Institution.name.asc(), Institution.id.asc())
    )

    affiliations: dict[UUID, list[Affiliation]] = {pid: [] for pid in page_ids}
    for row in (await session.execute(stmt)).mappings().all():
        city = None
        if row['city_id'] is not None:
            city = CityRef(id=row['city_id'], name=row['city_name'])
        affiliations[row['researcher_id']].append(
            Affiliation(
                institution=InstitutionRef.from_row(row),
                workload=row['workload'],
                identity_territory=row['identity_territory'],
                city=city,
            )
        )
    return affiliations


async def fetch_matches(
    session: AsyncSession,
    page_ids: list[UUID],
    q: Optional[str],
    limit: int = 3,
) -> dict[UUID, MatchesSummary]:
    """Busca evidências de match por pesquisador (Queries C1 e C2)."""
    if not page_ids or not q or not q.strip():
        return {}

    str_page_ids = [str(pid) for pid in page_ids]
    clean_q = q.strip()

    c1_stmt = text(
        """
        WITH q AS (SELECT websearch_to_tsquery('pt_unaccent', :q) AS tsq)
        SELECT p.researcher_id, m.source_type, m.source_id, m.title,
               m.year_, m.rank,
               ts_headline(
                   'pt_unaccent',
                   coalesce(
                       substring(oa.abstract from 1 for 2000), m.title, ''
                   ),
                   q.tsq,
                   'StartSel=[[, StopSel=]]'
               ) AS snippet
        FROM unnest(CAST(:page_ids AS uuid[])) AS p(researcher_id)
        CROSS JOIN q
        CROSS JOIN LATERAL (
            SELECT d.source_type, d.source_id, d.title, d.year_,
                   ts_rank(d.search_vector, q.tsq) AS rank
            FROM mv_search_documents d
            WHERE d.researcher_id = p.researcher_id
              AND d.search_vector @@ q.tsq
            UNION ALL
            SELECT 'PROFILE'::text AS source_type,
                   r_prof.researcher_id AS source_id,
                   r_prof.name AS title, NULL::int AS year_,
                   ts_rank(r_prof.profile_vector, q.tsq) AS rank
            FROM mv_researcher_search r_prof
            WHERE r_prof.researcher_id = p.researcher_id
              AND r_prof.profile_vector @@ q.tsq
            ORDER BY rank DESC, source_id
            LIMIT :n
        ) m
        LEFT JOIN openalex_article oa ON oa.article_id = m.source_id;
        """
    )

    c2_stmt = text(
        """
        WITH q AS (SELECT websearch_to_tsquery('pt_unaccent', :q) AS tsq)
        SELECT d.researcher_id, d.source_type, count(*) AS n
        FROM mv_search_documents d, q
        WHERE d.researcher_id = ANY(CAST(:page_ids AS uuid[]))
          AND d.search_vector @@ q.tsq
        GROUP BY d.researcher_id, d.source_type;
        """
    )

    c1_res = await session.execute(
        c1_stmt,
        {'q': clean_q, 'page_ids': str_page_ids, 'n': limit},
    )
    c2_res = await session.execute(
        c2_stmt,
        {'q': clean_q, 'page_ids': str_page_ids},
    )

    by_type_map: dict[UUID, dict[str, int]] = {pid: {} for pid in page_ids}
    total_map: dict[UUID, int] = {pid: 0 for pid in page_ids}
    for row in c2_res.mappings().all():
        r_id = row['researcher_id']
        st = row['source_type']
        cnt = int(row['n'])
        by_type_map[r_id][st] = cnt
        total_map[r_id] += cnt

    items_map: dict[UUID, list[MatchItem]] = {pid: [] for pid in page_ids}
    for row in c1_res.mappings().all():
        r_id = row['researcher_id']
        items_map[r_id].append(
            MatchItem(
                source_type=row['source_type'],
                source_id=row['source_id'],
                title=row['title'],
                year=row['year_'],
                snippet=row['snippet'],
            )
        )

    return {
        pid: MatchesSummary(
            total=total_map.get(pid, 0),
            by_type=by_type_map.get(pid, {}),
            items=items_map.get(pid, []),
        )
        for pid in page_ids
    }


async def _fetch_entity_facet(  # noqa: PLR0913
    session: AsyncSession,
    filters: ResearcherFilter,
    *,
    filter_key: str,
    array_column: ColumnElement,
    entity: type,
    entity_id: InstrumentedAttribute,
    selected: list[UUID],
    limit: int,
) -> FacetResult:
    """Facet disjuntivo sobre uma coluna de array de ids da MV.

    Devolve os `limit` valores com mais pesquisadores (desempate por nome)
    e sempre inclui os valores selecionados no filtro, mesmo fora do top ou
    com contagem zero, para que o frontend não perca o item marcado.
    """
    conditions = build_researcher_conditions(
        filters, exclude=frozenset({filter_key})
    )
    r = mv_researcher_search

    unnested = select(
        r.c.researcher_id,
        func.unnest(array_column).label('entity_id'),
    )
    if conditions:
        unnested = unnested.where(and_(*conditions))
    unnested = unnested.subquery()

    agg = (
        select(
            unnested.c.entity_id,
            func.count(func.distinct(unnested.c.researcher_id)).label('n'),
        )
        .group_by(unnested.c.entity_id)
        .subquery()
    )

    count_col = func.coalesce(agg.c.n, 0)
    is_selected = entity_id.in_(selected) if selected else false()
    ranked = (
        select(
            entity_id.label('value'),
            entity.name.label('label'),
            entity.acronym.label('acronym'),
            count_col.label('count'),
            is_selected.label('selected'),
            func
            .row_number()
            .over(
                order_by=(count_col.desc(), entity.name.asc(), entity_id.asc())
            )
            .label('rank'),
            func.count(agg.c.entity_id).over().label('total'),
        )
        .select_from(entity)
        .outerjoin(agg, agg.c.entity_id == entity_id)
        .where(or_(agg.c.entity_id.isnot(None), is_selected))
        .subquery()
    )
    stmt = (
        select(ranked)
        .where(or_(ranked.c.rank <= limit, ranked.c.selected))
        .order_by(ranked.c.rank)
    )

    rows = (await session.execute(stmt)).mappings().all()
    return _to_facet_result(rows)


def _to_facet_result(rows: Sequence[RowMapping]) -> FacetResult:
    return FacetResult(
        total=rows[0]['total'] if rows else 0,
        items=[
            FacetItem(
                value=str(row['value']),
                label=str(row['label']),
                count=row['count'],
                acronym=row.get('acronym'),
                selected=row.get('selected', False),
            )
            for row in rows
        ],
    )


async def fetch_institution_facet(
    session: AsyncSession,
    filters: ResearcherFilter,
    limit: int = 20,
) -> FacetResult:
    """Calcula facet de instituições com faceting disjuntivo."""
    return await _fetch_entity_facet(
        session,
        filters,
        filter_key='institution_id',
        array_column=mv_researcher_search.c.institution_ids,
        entity=Institution,
        entity_id=Institution.id,
        selected=filters.institution_id,
        limit=limit,
    )


async def fetch_graduate_program_facet(
    session: AsyncSession,
    filters: ResearcherFilter,
    limit: int = 20,
) -> FacetResult:
    """Calcula facet de programas de pós-graduação com faceting disjuntivo."""
    return await _fetch_entity_facet(
        session,
        filters,
        filter_key='graduate_program_id',
        array_column=mv_researcher_search.c.graduate_program_ids,
        entity=GraduateProgramDB,
        entity_id=GraduateProgramDB.graduate_program_id,
        selected=filters.graduate_program_id,
        limit=limit,
    )


async def fetch_year_facet(
    session: AsyncSession,
    filters: ResearcherFilter,
    limit: int = 20,
) -> FacetResult:
    """Calcula histograma de anos com unnest."""
    exclude = frozenset({'year_range'})
    conditions = build_researcher_conditions(filters, exclude=exclude)
    r = mv_researcher_search

    subq = select(
        r.c.researcher_id,
        func.unnest(r.c.production_years).label('yr'),
    )
    if conditions:
        subq = subq.where(and_(*conditions))
    subq = subq.subquery()

    stmt = (
        select(
            subq.c.yr.label('value'),
            subq.c.yr.label('label'),
            func.count(func.distinct(subq.c.researcher_id)).label('count'),
            func.count().over().label('total'),
        )
        .group_by(subq.c.yr)
        .order_by(literal_column('count').desc(), subq.c.yr.desc())
        .limit(limit)
    )

    rows = (await session.execute(stmt)).mappings().all()
    return _to_facet_result(rows)


async def fetch_source_type_facet(
    session: AsyncSession,
    filters: ResearcherFilter,
    limit: int = 20,
) -> FacetResult:
    """Calcula facet de tipos de fontes documentais (apenas com q)."""
    if not filters.q or not filters.q.strip():
        return FacetResult(total=0, items=[])

    conditions = build_researcher_conditions(filters)
    clean_q = filters.q.strip()
    tsq = func.websearch_to_tsquery('pt_unaccent', clean_q)

    r = mv_researcher_search
    d = mv_search_documents

    matching_r = select(r.c.researcher_id)
    if conditions:
        matching_r = matching_r.where(and_(*conditions))
    matching_subq = matching_r.subquery()

    stmt = (
        select(
            d.c.source_type.label('value'),
            d.c.source_type.label('label'),
            func.count(func.distinct(d.c.researcher_id)).label('count'),
            func.count().over().label('total'),
        )
        .where(
            and_(
                d.c.researcher_id.in_(select(matching_subq.c.researcher_id)),
                d.c.search_vector.op('@@')(tsq),
            )
        )
        .group_by(d.c.source_type)
        .order_by(literal_column('count').desc(), d.c.source_type.asc())
        .limit(limit)
    )

    rows = (await session.execute(stmt)).mappings().all()
    return _to_facet_result(rows)


FACET_BUILDERS = {
    'institution': fetch_institution_facet,
    'graduate_program': fetch_graduate_program_facet,
    'year': fetch_year_facet,
    'source_type': fetch_source_type_facet,
}


async def fetch_requested_facets(
    session: AsyncSession,
    filters: ResearcherFilter,
    requested_facets: list[str],
    limit: int = 20,
) -> dict[str, FacetResult]:
    """Calcula todos os facets requisitados respeitando o orçamento."""
    facets_result: dict[str, FacetResult] = {}
    for facet_name in requested_facets:
        builder = FACET_BUILDERS.get(facet_name)
        if builder:
            facets_result[facet_name] = await builder(
                session, filters, limit=limit
            )
    return facets_result
