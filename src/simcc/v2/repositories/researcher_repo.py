"""Repositório de acesso a dados para pesquisadores v2 sobre MVs."""

from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Float,
    Select,
    String,
    and_,
    cast,
    func,
    literal_column,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.graduate_program import (
    GraduateProgram as GraduateProgramDB,
)
from simcc.v2.repositories.researcher_filters import (
    build_researcher_conditions,
)
from simcc.v2.repositories.search_tables import (
    mv_researcher_search,
    mv_search_documents,
)
from simcc.v2.schemas.filters import ResearcherFilter
from simcc.v2.schemas.params import PaginationParams, SortParams
from simcc.v2.schemas.researcher import (
    FacetItem,
    MatchesSummary,
    MatchItem,
    Researcher,
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
) -> tuple[list[Researcher], int]:
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
    stmt = select(r.c.researcher_id, r.c.name)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = _apply_sorting(stmt, sort, filters)

    offset = max(0, (pagination.page - 1) * pagination.per_page)
    stmt = stmt.offset(offset).limit(pagination.per_page)

    result = await session.execute(stmt)
    rows = result.mappings().all()
    data = [
        Researcher(
            researcher_id=row['researcher_id'],
            name=row['name'],
        )
        for row in rows
    ]

    return data, total_items


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


async def fetch_institution_facet(
    session: AsyncSession,
    filters: ResearcherFilter,
    limit: int = 20,
) -> list[FacetItem]:
    """Calcula facet de instituições com faceting disjuntivo."""
    exclude = frozenset({'institution_id'})
    conditions = build_researcher_conditions(filters, exclude=exclude)
    r = mv_researcher_search

    stmt = (
        select(
            r.c.institution_id.cast(String).label('value'),
            func.coalesce(
                r.c.institution_name,
                r.c.institution_acronym,
                'Outra Instituição',
            ).label('label'),
            func.count(r.c.researcher_id).label('count'),
        )
        .where(r.c.institution_id.isnot(None))
        .group_by(
            r.c.institution_id, r.c.institution_name, r.c.institution_acronym
        )
        .order_by(literal_column('count').desc())
        .limit(limit)
    )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    rows = (await session.execute(stmt)).mappings().all()
    return [
        FacetItem(
            value=row['value'],
            label=row['label'],
            count=row['count'],
        )
        for row in rows
    ]


async def fetch_graduate_program_facet(
    session: AsyncSession,
    filters: ResearcherFilter,
    limit: int = 20,
) -> list[FacetItem]:
    """Calcula facet de programas de pós-graduação com unnest."""
    exclude = frozenset({'graduate_program_id'})
    conditions = build_researcher_conditions(filters, exclude=exclude)
    r = mv_researcher_search

    subq = select(
        r.c.researcher_id,
        func.unnest(r.c.graduate_program_ids).label('gp_id'),
    )
    if conditions:
        subq = subq.where(and_(*conditions))
    subq = subq.subquery()

    main_stmt = (
        select(
            GraduateProgramDB.id.cast(String).label('value'),
            func.coalesce(
                GraduateProgramDB.name,
                GraduateProgramDB.acronym,
                'Programa',
            ).label('label'),
            func.count(func.distinct(subq.c.researcher_id)).label('count'),
        )
        .join(subq, subq.c.gp_id == GraduateProgramDB.id)
        .group_by(
            GraduateProgramDB.id,
            GraduateProgramDB.name,
            GraduateProgramDB.acronym,
        )
        .order_by(literal_column('count').desc())
        .limit(limit)
    )

    rows = (await session.execute(main_stmt)).mappings().all()
    return [
        FacetItem(
            value=row['value'],
            label=row['label'],
            count=row['count'],
        )
        for row in rows
    ]


async def fetch_year_facet(
    session: AsyncSession,
    filters: ResearcherFilter,
    limit: int = 20,
) -> list[FacetItem]:
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
            subq.c.yr.cast(String).label('value'),
            subq.c.yr.cast(String).label('label'),
            func.count(func.distinct(subq.c.researcher_id)).label('count'),
        )
        .group_by(subq.c.yr)
        .order_by(literal_column('count').desc(), subq.c.yr.desc())
        .limit(limit)
    )

    rows = (await session.execute(stmt)).mappings().all()
    return [
        FacetItem(
            value=row['value'],
            label=row['label'],
            count=row['count'],
        )
        for row in rows
    ]


async def fetch_source_type_facet(
    session: AsyncSession,
    filters: ResearcherFilter,
    limit: int = 20,
) -> list[FacetItem]:
    """Calcula facet de tipos de fontes documentais (apenas com q)."""
    if not filters.q or not filters.q.strip():
        return []

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
        )
        .where(
            and_(
                d.c.researcher_id.in_(select(matching_subq.c.researcher_id)),
                d.c.search_vector.op('@@')(tsq),
            )
        )
        .group_by(d.c.source_type)
        .order_by(literal_column('count').desc())
        .limit(limit)
    )

    rows = (await session.execute(stmt)).mappings().all()
    return [
        FacetItem(
            value=row['value'],
            label=row['label'],
            count=row['count'],
        )
        for row in rows
    ]


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
) -> dict[str, list[FacetItem]]:
    """Calcula todos os facets requisitados respeitando o orçamento."""
    facets_result: dict[str, list[FacetItem]] = {}
    for facet_name in requested_facets:
        builder = FACET_BUILDERS.get(facet_name)
        if builder:
            facets_result[facet_name] = await builder(
                session, filters, limit=limit
            )
    return facets_result
