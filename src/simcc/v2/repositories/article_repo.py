"""Repositório de dados para artigos científicos v2.

Opera sobre a visão materializada mv_canonical_articles.
"""

from typing import Any, Mapping, Optional
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    and_,
    cast,
    func,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.repositories.search_tables import mv_canonical_articles
from simcc.v2.schemas.params import PaginationParams
from simcc.v2.schemas.production import (
    ArticleFilter,
    ArticleMatch,
    ArticleSort,
)

a = mv_canonical_articles


def search_tsquery(filters: ArticleFilter) -> Optional[ColumnElement]:
    """Retorna o tsquery para busca textual ou None se q não foi informado."""
    if not filters.q or not filters.q.strip():
        return None
    return func.websearch_to_tsquery('pt_unaccent', filters.q.strip())


def build_article_conditions(
    filters: ArticleFilter,
) -> list[ColumnElement[bool]]:
    """Gera a lista de condições SQL para filtrar artigos sobre a MV."""
    conds: list[ColumnElement[bool]] = []

    tsq = search_tsquery(filters)
    if tsq is not None:
        conds.append(a.c.search_vector.op('@@')(tsq))

    if filters.year_start is not None:
        conds.append(a.c.year >= filters.year_start)

    if filters.year_end is not None:
        conds.append(a.c.year <= filters.year_end)

    if filters.qualis:
        conds.append(a.c.qualis.in_(filters.qualis))

    if filters.researcher_id:
        conds.append(
            a.c.researcher_ids.op('&&')(
                cast(filters.researcher_id, ARRAY(PG_UUID(as_uuid=True)))
            )
        )

    if filters.institution_id:
        conds.append(
            a.c.institution_ids.op('&&')(
                cast(filters.institution_id, ARRAY(PG_UUID(as_uuid=True)))
            )
        )

    if filters.graduate_program_id:
        conds.append(
            a.c.graduate_program_ids.op('&&')(
                cast(filters.graduate_program_id, ARRAY(PG_UUID(as_uuid=True)))
            )
        )

    if filters.has_open_access is True:
        conds.append(a.c.has_open_access_pdf.is_(True))
    elif filters.has_open_access is False:
        conds.append(a.c.has_open_access_pdf.is_(False))

    return conds


def _order_clauses(
    sort: ArticleSort,
    tsq: Optional[ColumnElement],
) -> list[ColumnElement]:
    """Define a ordenação dos artigos."""
    clauses: list[ColumnElement] = []

    if sort.by == 'relevance' and tsq is not None:
        rank = func.ts_rank(a.c.search_vector, tsq)
        clauses.append(rank.desc() if sort.order == 'desc' else rank.asc())
        clauses.append(a.c.citations_count.desc())
        clauses.append(a.c.year.desc().nulls_last())
    elif sort.by == 'year':
        col = (
            a.c.year.desc().nulls_last()
            if sort.order == 'desc'
            else a.c.year.asc().nulls_last()
        )
        clauses.append(col)
        clauses.append(a.c.citations_count.desc())
    elif sort.by == 'citations':
        col = (
            a.c.citations_count.desc()
            if sort.order == 'desc'
            else a.c.citations_count.asc()
        )
        clauses.append(col)
        clauses.append(a.c.year.desc().nulls_last())
    elif sort.by == 'title':
        col = a.c.title.desc() if sort.order == 'desc' else a.c.title.asc()
        clauses.append(col)
    else:
        # Fallback default
        clauses.append(a.c.year.desc().nulls_last())
        clauses.append(a.c.citations_count.desc())

    clauses.append(a.c.canonical_id)
    return clauses


async def count_articles(
    session: AsyncSession,
    filters: ArticleFilter,
) -> int:
    """Retorna a contagem exata de artigos para os filtros dados."""
    conds = build_article_conditions(filters)
    stmt = select(func.count()).select_from(a)
    if conds:
        stmt = stmt.where(and_(*conds))
    res = await session.execute(stmt)
    return res.scalar_one()


async def search_articles(
    session: AsyncSession,
    filters: ArticleFilter,
    sort: ArticleSort,
    pagination: PaginationParams,
) -> list[Mapping[str, Any]]:
    """Consulta paginada de artigos com ordenação e filtros."""
    conds = build_article_conditions(filters)
    tsq = search_tsquery(filters)
    stmt = select(a)
    if conds:
        stmt = stmt.where(and_(*conds))
    stmt = stmt.order_by(*_order_clauses(sort, tsq))
    stmt = stmt.limit(pagination.per_page).offset(
        (pagination.page - 1) * pagination.per_page
    )
    res = await session.execute(stmt)
    return res.mappings().all()


async def get_article_by_id(
    session: AsyncSession,
    article_id: UUID | str,
) -> Optional[Mapping[str, Any]]:
    """Busca o artigo por canonical_id, production_id ou DOI."""
    target_str = str(article_id).strip()
    try:
        uid = UUID(target_str)
        stmt = select(a).where(
            or_(
                a.c.canonical_id == uid,
                a.c.production_ids.op('@>')(
                    cast([uid], ARRAY(PG_UUID(as_uuid=True)))
                ),
            )
        )
    except ValueError:
        stmt = select(a).where(func.lower(a.c.doi) == target_str.lower())

    res = await session.execute(stmt)
    return res.mappings().first()


async def get_article_snippets(
    session: AsyncSession,
    canonical_ids: list[UUID],
    q: str,
) -> dict[UUID, list[ArticleMatch]]:
    """Gera snippets com termos destacados em <b> para os artigos da página."""
    if not canonical_ids or not q.strip():
        return {}

    tsq = func.websearch_to_tsquery('pt_unaccent', q.strip())
    stmt = select(
        a.c.canonical_id,
        func.ts_headline(
            'pt_unaccent',
            a.c.title,
            tsq,
            'StartSel=<b>, StopSel=</b>, HighlightAll=TRUE',
        ).label('title_hl'),
        func.ts_headline(
            'pt_unaccent',
            func.coalesce(a.c.abstract, ''),
            tsq,
            'StartSel=<b>, StopSel=</b>, MaxWords=35, MinWords=15',
        ).label('abstract_hl'),
    ).where(a.c.canonical_id.in_(canonical_ids))

    res = await session.execute(stmt)
    results: dict[UUID, list[ArticleMatch]] = {}
    for row in res.mappings().all():
        cid = row['canonical_id']
        matches: list[ArticleMatch] = []
        title_hl = row['title_hl'] or ''
        abstract_hl = row['abstract_hl'] or ''
        if '<b>' in title_hl:
            matches.append(ArticleMatch(field='title', snippet=title_hl))
        if '<b>' in abstract_hl:
            matches.append(ArticleMatch(field='abstract', snippet=abstract_hl))
        if matches:
            results[cid] = matches

    return results
