"""Repositório de acesso a dados para pesquisadores v2 sobre MVs."""

from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Float,
    Integer,
    Select,
    and_,
    cast,
    func,
    literal,
    literal_column,
    null,
    select,
    union_all,
)
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.institution import Institution
from simcc.core.db.models.location import City
from simcc.core.db.models.openalex import OpenAlexArticle
from simcc.core.db.models.researcher_institution import ResearcherInstitution
from simcc.v2.repositories.researcher_filters import (
    build_researcher_conditions,
    document_conditions,
    profile_counts,
    search_tsquery,
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
    MatchesSummary,
    MatchItem,
    ResearcherCounts,
    ResearcherSummary,
    researcher_image_url,
)

r = mv_researcher_search
d = mv_search_documents

SORTABLE = {
    'name': r.c.name,
    'id': r.c.researcher_id,
}


def _relevance_score(filters: ResearcherFilter, tsq) -> ColumnElement:
    """Perfil × 1.5 + melhor obra + ln(obras que contam + 1)."""
    doc_relevance = (
        select(
            func.coalesce(func.max(func.ts_rank(d.c.search_vector, tsq)), 0.0)
            + func.ln(
                func.coalesce(cast(func.count(d.c.source_id), Float), 0.0)
                + 1.0
            )
        )
        .where(
            d.c.researcher_id == r.c.researcher_id,
            *document_conditions(filters),
        )
        .scalar_subquery()
    )
    if not profile_counts(filters):
        return doc_relevance
    return func.ts_rank(r.c.profile_vector, tsq) * 1.5 + doc_relevance


def _apply_sorting(
    stmt: Select,
    sort: SortParams,
    filters: ResearcherFilter,
) -> Select:
    """Aplica ordenação determinística ou por relevância."""
    tsq = search_tsquery(filters)
    if sort.sort_by == 'relevance' and tsq is not None:
        score = _relevance_score(filters, tsq)
        direction = score.desc() if sort.sort_order == 'desc' else score.asc()
        return stmt.order_by(
            direction, r.c.name.asc(), r.c.researcher_id.asc()
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
    filters: ResearcherFilter,
    limit: int = 3,
) -> dict[UUID, MatchesSummary]:
    """Evidências por pesquisador da página: as `limit` obras (ou o perfil)
    que mais casam com `q`, e a contagem por tipo. Usa as mesmas regras de
    obra da busca (`document_conditions`), incluindo anos e `source_type`."""
    tsq = search_tsquery(filters)
    if not page_ids or tsq is None:
        return {}

    doc_conds = [
        d.c.researcher_id.in_(page_ids),
        *document_conditions(filters),
    ]

    candidates = select(
        d.c.researcher_id,
        d.c.source_type,
        d.c.source_id,
        d.c.title,
        d.c.year_,
        func.ts_rank(d.c.search_vector, tsq).label('rank'),
    ).where(*doc_conds)
    if profile_counts(filters):
        candidates = union_all(
            candidates,
            select(
                r.c.researcher_id,
                literal('PROFILE').label('source_type'),
                r.c.researcher_id.label('source_id'),
                r.c.name.label('title'),
                null().cast(Integer).label('year_'),
                func.ts_rank(r.c.profile_vector, tsq).label('rank'),
            ).where(
                r.c.researcher_id.in_(page_ids),
                r.c.profile_vector.op('@@')(tsq),
            ),
        )
    candidates = candidates.subquery()

    ranked = select(
        candidates,
        func
        .row_number()
        .over(
            partition_by=candidates.c.researcher_id,
            order_by=(candidates.c.rank.desc(), candidates.c.source_id),
        )
        .label('position'),
    ).subquery()

    snippet_source = func.coalesce(
        func.substring(OpenAlexArticle.abstract, 1, 2000), ranked.c.title, ''
    )
    items_stmt = (
        select(
            ranked.c.researcher_id,
            ranked.c.source_type,
            ranked.c.source_id,
            ranked.c.title,
            ranked.c.year_,
            func.ts_headline(
                literal_column("'pt_unaccent'::regconfig"),
                snippet_source,
                tsq,
                literal_column("'StartSel=[[, StopSel=]]'"),
            ).label('snippet'),
        )
        .outerjoin(
            OpenAlexArticle, OpenAlexArticle.article_id == ranked.c.source_id
        )
        .where(ranked.c.position <= limit)
        .order_by(ranked.c.researcher_id, ranked.c.position)
    )
    counts_stmt = (
        select(d.c.researcher_id, d.c.source_type, func.count().label('n'))
        .where(*doc_conds)
        .group_by(d.c.researcher_id, d.c.source_type)
    )

    items_rows = (await session.execute(items_stmt)).mappings().all()
    counts_rows = (await session.execute(counts_stmt)).mappings().all()

    by_type_map: dict[UUID, dict[str, int]] = {pid: {} for pid in page_ids}
    for row in counts_rows:
        by_type_map[row['researcher_id']][row['source_type']] = row['n']

    items_map: dict[UUID, list[MatchItem]] = {pid: [] for pid in page_ids}
    for row in items_rows:
        items_map[row['researcher_id']].append(
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
            total=sum(by_type_map[pid].values()),
            by_type=by_type_map[pid],
            items=items_map[pid],
        )
        for pid in page_ids
    }
