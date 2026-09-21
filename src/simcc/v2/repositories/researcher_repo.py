import logging
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.ai import SearchDocumentResearcher
from simcc.core.db.models.graduate_program import GraduateProgramResearcher
from simcc.core.db.models.production import BibliographicProduction
from simcc.core.db.models.researcher import Researcher

logger = logging.getLogger(__name__)

MAX_MATCHES_PER_RESEARCHER = 3


def _build_filter_conditions(filters: dict[str, Any]) -> list:
    conditions = []
    institution_id = filters.get('institution_id')
    if institution_id:
        conditions.append(Researcher.institution_id == institution_id)

    graduate_program_id = filters.get('graduate_program_id')
    if graduate_program_id:
        sub_gp = select(GraduateProgramResearcher.researcher_id).filter(
            GraduateProgramResearcher.graduate_program_id
            == graduate_program_id
        )
        conditions.append(Researcher.id.in_(sub_gp))

    year_start = filters.get('year_start')
    year_end = filters.get('year_end')
    if year_start is not None or year_end is not None:
        p_conds = []
        if year_start is not None:
            p_conds.append(BibliographicProduction.year_ >= year_start)
        if year_end is not None:
            p_conds.append(BibliographicProduction.year_ <= year_end)
        sub_bp = select(BibliographicProduction.researcher_id).filter(
            and_(*p_conds)
        )
        conditions.append(Researcher.id.in_(sub_bp))

    return conditions


def _apply_sorting(stmt, sort: dict[str, str]):
    sort_by = sort.get('by', 'name')
    sort_order = sort.get('order', 'asc')
    order_col = getattr(Researcher, sort_by, Researcher.name)
    return stmt.order_by(
        order_col.desc() if sort_order == 'desc' else order_col.asc()
    )


async def _fetch_from_orm_fallback(
    session: AsyncSession,
    query_params: dict[str, Any],
    embedding_vector: list[float] | None = None,
    cosine_threshold: float = 0.65,
) -> tuple[list[dict[str, Any]], int]:
    filters = query_params.get('filters', {})
    pagination = query_params.get('pagination', {})
    sort = query_params.get('sort', {})
    conditions = _build_filter_conditions(filters)

    if embedding_vector is not None:
        stmt = select(Researcher).join(
            SearchDocumentResearcher,
            SearchDocumentResearcher.researcher_id == Researcher.id,
        )
        dist_expr = SearchDocumentResearcher.embedding.cosine_distance(
            embedding_vector
        )
        conditions.append(dist_expr <= cosine_threshold)
        stmt = stmt.filter(and_(*conditions)).order_by(dist_expr.asc())
    else:
        stmt = select(Researcher)
        q = filters.get('q')
        if q:
            for token in q.split():
                clean_tok = token.strip()
                if clean_tok:
                    conditions.append(Researcher.name.ilike(f'%{clean_tok}%'))
        if conditions:
            stmt = stmt.filter(and_(*conditions))
        stmt = _apply_sorting(stmt, sort)

    count_subq = stmt.order_by(None).subquery()
    count_stmt = select(func.count()).select_from(count_subq)
    total_items = (await session.execute(count_stmt)).scalar_one() or 0

    page = pagination.get('page', 1)
    per_page = pagination.get('per_page', 20)
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(stmt)
    records = [
        {
            'researcher_id': str(r.id),
            'name': r.name,
            'relevance_score': None,
        }
        for r in result.scalars().all()
    ]
    return records, total_items


def _build_mv_filters(
    filters: dict[str, Any], params: dict[str, Any]
) -> list[str]:
    clauses: list[str] = []
    inst_id = filters.get('institution_id')
    if inst_id:
        params['inst_id'] = str(inst_id)
        clauses.append('institution_id = CAST(:inst_id AS uuid)')

    gp_id = filters.get('graduate_program_id')
    if gp_id:
        params['gp_id'] = str(gp_id)
        clauses.append('graduate_program_ids @> ARRAY[CAST(:gp_id AS uuid)]')

    y_start = filters.get('year_start')
    y_end = filters.get('year_end')
    if y_start is not None or y_end is not None:
        y_conds: list[str] = []
        if y_start is not None:
            params['y_start'] = int(y_start)
            y_conds.append('y >= :y_start')
        if y_end is not None:
            params['y_end'] = int(y_end)
            y_conds.append('y <= :y_end')
        clauses.append(
            'EXISTS (SELECT 1 FROM unnest(production_years) y '
            f'WHERE {" AND ".join(y_conds)})'
        )
    return clauses


def _build_mv_order(sort: dict[str, str], has_q: bool) -> tuple[str, str]:
    if has_q:
        select_clause = (
            'SELECT researcher_id, name, '
            "ts_rank_cd('{0.1, 0.2, 0.4, 1.0}', search_vector, query) "
            'AS relevance_score, COUNT(*) OVER() AS total_items '
            'FROM mv_researcher_search, '
            "websearch_to_tsquery('pt_unaccent', :q) query"
        )
        order_clause = ' ORDER BY relevance_score DESC, name ASC'
        return select_clause, order_clause

    select_clause = (
        'SELECT researcher_id, name, NULL::float AS relevance_score, '
        'COUNT(*) OVER() AS total_items FROM mv_researcher_search'
    )
    sort_by = sort.get('by', 'name')
    sort_order = str(sort.get('order', 'asc')).lower()
    col = 'name' if sort_by != 'researcher_id' else 'researcher_id'
    direction = 'DESC' if sort_order == 'desc' else 'ASC'
    order_clause = f' ORDER BY {col} {direction}'
    return select_clause, order_clause


def _build_mv_query(
    query_params: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    filters = query_params.get('filters', {})
    pagination = query_params.get('pagination', {})
    page = pagination.get('page', 1)
    per_page = pagination.get('per_page', 20)
    q = filters.get('q')

    params: dict[str, Any] = {
        'limit': per_page,
        'offset': (page - 1) * per_page,
    }
    where_clauses = _build_mv_filters(filters, params)
    if q:
        params['q'] = q
        where_clauses.append('search_vector @@ query')

    select_clause, order_clause = _build_mv_order(
        query_params.get('sort', {}), bool(q)
    )
    where_sql = (
        f' WHERE {" AND ".join(where_clauses)}' if where_clauses else ''
    )
    full_sql = (
        f'{select_clause}{where_sql}{order_clause} LIMIT :limit OFFSET :offset'
    )
    return full_sql, params


async def _fetch_from_mv(
    session: AsyncSession,
    query_params: dict[str, Any],
) -> tuple[list[dict[str, Any]], int] | None:
    full_sql, params = _build_mv_query(query_params)

    try:
        res = await session.execute(text(full_sql), params)
        rows = res.mappings().all()
    except Exception as exc:
        logger.warning(
            'Falha na consulta a mv_researcher_search: %s. '
            'Realizando rollback e fallback.',
            exc,
        )
        await session.rollback()
        return None

    if not rows:
        return [], 0

    total_items = rows[0]['total_items']
    records = [
        {
            'researcher_id': str(row['researcher_id']),
            'name': row['name'],
            'relevance_score': (
                round(float(row['relevance_score']), 4)
                if row['relevance_score'] is not None
                else None
            ),
        }
        for row in rows
    ]
    return records, total_items


async def fetch_researchers_v2(
    session: AsyncSession,
    query_params: dict[str, Any],
    embedding_vector: list[float] | None = None,
    cosine_threshold: float = 0.65,
) -> tuple[list[dict[str, Any]], int]:
    # Tenta consultar primeiramente a MV agregada (Fase 1 com FTS)
    mv_result = await _fetch_from_mv(session, query_params)
    if mv_result is not None:
        return mv_result

    # Fallback seguro para ORM
    return await _fetch_from_orm_fallback(
        session=session,
        query_params=query_params,
        embedding_vector=embedding_vector,
        cosine_threshold=cosine_threshold,
    )


async def fetch_matched_in_v2(
    session: AsyncSession,
    researcher_ids: list[UUID | str],
    search_term: str,
) -> dict[str, list[dict[str, Any]]]:
    if not researcher_ids or not search_term:
        return {}

    sql = text("""
    WITH raw_matches AS (
        SELECT
            source_type,
            source_id,
            researcher_id,
            title,
            CASE
                WHEN search_vector @@ query THEN 'title'
                ELSE 'abstract'
            END AS field,
            ts_rank_cd(search_vector, query) AS field_score,
            ts_headline(
                'pt_unaccent',
                coalesce(abstract, title),
                query,
                'MaxFragments=1, MaxWords=25, MinWords=10, '
                'StartSel=<mark>, StopSel=</mark>'
            ) AS snippet
        FROM (
            SELECT * FROM mv_search_articles
            UNION ALL SELECT * FROM mv_search_books
            UNION ALL SELECT * FROM mv_search_patents
            UNION ALL SELECT * FROM mv_search_software
        ) all_sources,
        websearch_to_tsquery('pt_unaccent', :q) query
        WHERE researcher_id = ANY(:r_ids)
          AND search_vector @@ query
    )
    SELECT
        source_type,
        source_id,
        researcher_id,
        title,
        field,
        field_score,
        snippet
    FROM raw_matches
    ORDER BY researcher_id, field_score DESC;
    """)

    params = {
        'q': search_term,
        'r_ids': [UUID(str(r)) for r in researcher_ids],
    }

    try:
        res = await session.execute(sql, params)
        rows = res.mappings().all()
    except Exception as exc:
        logger.warning('Falha em fetch_matched_in_v2: %s', exc)
        await session.rollback()
        return {}

    matched_map: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rid = str(row['researcher_id'])
        if rid not in matched_map:
            matched_map[rid] = []
        if len(matched_map[rid]) < MAX_MATCHES_PER_RESEARCHER:
            matched_map[rid].append({
                'source_type': row['source_type'],
                'source_id': (
                    str(row['source_id']) if row['source_id'] else None
                ),
                'field': row['field'],
                'title': row['title'],
                'snippet': row['snippet'],
                'score': (
                    round(float(row['field_score']), 4)
                    if row['field_score'] is not None
                    else None
                ),
                'match_type': 'fts',
            })
    return matched_map
