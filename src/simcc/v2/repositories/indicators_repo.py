"""Consultas da Fase 2: revistas, bolsistas, termos e indicadores."""

from typing import Optional
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Float,
    Table,
    cast,
    exists,
    func,
    literal_column,
    select,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.graduate_program import GraduateProgramResearcher
from simcc.core.db.models.institution import PeriodicalMagazine
from simcc.core.db.models.production import Foment
from simcc.core.db.models.researcher import Researcher
from simcc.core.db.models.researcher_institution import ResearcherInstitution
from simcc.core.stopwords import STOPWORDS
from simcc.v2.repositories import search_tables
from simcc.v2.repositories.production_repo import build_production_conditions
from simcc.v2.repositories.researcher_facets_repo import rank_facet_values
from simcc.v2.schemas.indicators import (
    Magazine,
    MagazineFilter,
    MagazineSort,
    Scholarship,
    ScholarshipFilter,
    ScholarshipSort,
    SeriesPoint,
    Term,
)
from simcc.v2.schemas.params import PaginationParams
from simcc.v2.schemas.production import ProductionBaseFilter
from simcc.v2.schemas.qualis import qualis_from_db, qualis_to_db
from simcc.v2.schemas.researcher import FacetResult

# Palavras com até este tamanho ficam fora da nuvem de termos
MIN_TERM_LENGTH = 3

# Tabela canônica de cada tipo de produção
PRODUCTION_TABLES: dict[str, Table] = {
    'article': search_tables.mv_canonical_articles,
    'book': search_tables.mv_canonical_books,
    'book_chapter': search_tables.mv_canonical_book_chapters,
    'software': search_tables.mv_canonical_software,
    'patent': search_tables.mv_canonical_patents,
    'event': search_tables.mv_canonical_events,
    'research_project': search_tables.mv_canonical_research_projects,
    'brand': search_tables.mv_canonical_brands,
    'guidance': search_tables.mv_canonical_guidance,
    'report': search_tables.mv_canonical_reports,
}


async def _page(session, stmt, count_stmt, pagination: PaginationParams):
    total = (await session.execute(count_stmt)).scalar() or 0
    if total == 0:
        return [], 0
    offset = (pagination.page - 1) * pagination.per_page
    rows = (
        (await session.execute(stmt.offset(offset).limit(pagination.per_page)))
        .mappings()
        .all()
    )
    return rows, total


def _ordered(column, order: str):
    return (column.desc() if order == 'desc' else column.asc()).nulls_last()


# =========================================================================
# Revistas
# =========================================================================

m = PeriodicalMagazine


def _magazine_conditions(
    filters: MagazineFilter, exclude: frozenset[str] = frozenset()
) -> list[ColumnElement]:
    conds = []
    if filters.q and filters.q.strip():
        conds.append(m.name.ilike(f'%{filters.q.strip()}%'))
    if filters.issn and 'issn' not in exclude:
        conds.append(m.issn.in_(filters.issn))
    if filters.qualis and 'qualis' not in exclude:
        conds.append(m.qualis.in_([qualis_to_db(v) for v in filters.qualis]))
    return conds


def _jcr_number():
    """JCR textual como número (vírgula decimal); inválido vira NULL."""
    text_value = func.replace(func.trim(m.jcr), ',', '.')
    return cast(
        func.nullif(func.substring(text_value, r'^\d+(?:\.\d+)?$'), ''),
        Float,
    )


async def fetch_magazines(
    session: AsyncSession,
    filters: MagazineFilter,
    pagination: PaginationParams,
    sort: MagazineSort,
) -> tuple[list[Magazine], int]:
    conds = _magazine_conditions(filters)
    sort_col = _jcr_number() if sort.sort_by == 'jcr' else m.name
    stmt = (
        select(m)
        .where(*conds)
        .order_by(_ordered(sort_col, sort.sort_order), m.id)
    )
    count_stmt = select(func.count(m.id)).where(*conds)
    total = (await session.execute(count_stmt)).scalar() or 0
    if total == 0:
        return [], 0
    offset = (pagination.page - 1) * pagination.per_page
    rows = (
        await session.execute(stmt.offset(offset).limit(pagination.per_page))
    ).scalars()
    return [_magazine(row) for row in rows], total


def _magazine(row: PeriodicalMagazine) -> Magazine:
    return Magazine.model_validate({
        'id': row.id,
        'name': row.name,
        'issn': row.issn,
        'qualis': row.qualis,
        'jcr': row.jcr,
        'jcr_link': row.jcr_link,
        'reference_period': row.reference_period,
    })


async def fetch_magazine(
    session: AsyncSession, magazine_id: UUID
) -> Optional[Magazine]:
    row = await session.get(PeriodicalMagazine, magazine_id)
    return _magazine(row) if row is not None else None


async def fetch_magazine_facets(
    session: AsyncSession,
    filters: MagazineFilter,
    requested: list[str],
    limit: int,
) -> dict[str, FacetResult]:
    facets = {}
    if 'qualis' in requested:
        pairs = select(m.id, m.qualis.label('value')).where(
            m.qualis.isnot(None),
            *_magazine_conditions(filters, frozenset({'qualis'})),
        )
        facet = await rank_facet_values(
            session,
            pairs,
            selected=[qualis_to_db(v) for v in filters.qualis],
            limit=limit,
        )
        items = []
        for item in facet.items:
            value = qualis_from_db(item.value)
            if value is None:
                facet.total -= 1
                continue
            item.value = item.label = value
            items.append(item)
        facet.items = items
        facet.param = 'qualis'
        facets['qualis'] = facet
    return facets


# =========================================================================
# Bolsistas
# =========================================================================

f = Foment
_SCHOLARSHIP_COLUMNS = {
    'modality': f.modality_name,
    'category_level': f.category_level_code,
}


def _scholarship_conditions(
    filters: ScholarshipFilter, exclude: frozenset[str] = frozenset()
) -> list[ColumnElement]:
    conds = []
    if filters.researcher_id:
        conds.append(f.researcher_id.in_(filters.researcher_id))
    if filters.institution_id:
        ri = ResearcherInstitution
        conds.append(
            exists().where(
                ri.researcher_id == f.researcher_id,
                ri.institution_id.in_(filters.institution_id),
            )
        )
    if filters.graduate_program_id:
        gpr = GraduateProgramResearcher
        conds.append(
            exists().where(
                gpr.researcher_id == f.researcher_id,
                gpr.graduate_program_id.in_(filters.graduate_program_id),
            )
        )
    for field, column in _SCHOLARSHIP_COLUMNS.items():
        values = getattr(filters, field)
        if values and field not in exclude:
            conds.append(column.in_(values))
    return conds


async def fetch_scholarships(
    session: AsyncSession,
    filters: ScholarshipFilter,
    pagination: PaginationParams,
    sort: ScholarshipSort,
) -> tuple[list[Scholarship], int]:
    r = Researcher
    conds = _scholarship_conditions(filters)
    sort_col = {
        'researcher_name': r.name,
        'modality': f.modality_name,
        'category_level': f.category_level_code,
    }[sort.sort_by]
    stmt = (
        select(f, r.name.label('researcher_name'))
        .join(r, r.id == f.researcher_id)
        .where(*conds)
        .order_by(_ordered(sort_col, sort.sort_order), r.name, f.id)
    )
    count_stmt = select(func.count(f.id)).where(*conds)
    rows, total = await _page(session, stmt, count_stmt, pagination)
    data = [
        Scholarship(
            id=row['Foment'].id,
            researcher={
                'id': row['Foment'].researcher_id,
                'name': row['researcher_name'],
            },
            modality=row['Foment'].modality_name,
            category_level=row['Foment'].category_level_code,
            call_title=row['Foment'].call_title,
            funding_program=row['Foment'].funding_program_name,
            institute=row['Foment'].institute_name,
            aid_quantity=row['Foment'].aid_quantity,
            scholarship_quantity=row['Foment'].scholarship_quantity,
        )
        for row in rows
    ]
    return data, total


async def fetch_scholarship_facets(
    session: AsyncSession,
    filters: ScholarshipFilter,
    requested: list[str],
    limit: int,
) -> dict[str, FacetResult]:
    facets = {}
    for name in requested:
        column = _SCHOLARSHIP_COLUMNS[name]
        pairs = select(f.id, column.label('value')).where(
            column.isnot(None),
            *_scholarship_conditions(filters, frozenset({name})),
        )
        facet = await rank_facet_values(
            session, pairs, selected=getattr(filters, name), limit=limit
        )
        facet.param = name
        facets[name] = facet
    return facets


# =========================================================================
# Termos do pesquisador
# =========================================================================


async def fetch_researcher_terms(
    session: AsyncSession, researcher_id: UUID, limit: int
) -> list[Term]:
    """Palavras mais frequentes nos títulos das produções do pesquisador.

    Cada título conta uma vez por palavra. Palavras com até 3 letras e
    stopwords ficam de fora (mesma regra da V1).
    """
    target = cast([researcher_id], ARRAY(PG_UUID(as_uuid=True)))
    titles = union_all(*(
        select(table.c.title.label('title')).where(
            table.c.researcher_ids.op('@>')(target)
        )
        for table in PRODUCTION_TABLES.values()
    )).subquery()
    lexemes = select(
        func.unnest(
            func.tsvector_to_array(
                func.to_tsvector(
                    literal_column("'simple'::regconfig"),
                    func.unaccent(func.lower(titles.c.title)),
                )
            )
        ).label('lexeme')
    ).subquery()
    stmt = (
        select(lexemes.c.lexeme, func.count().label('n'))
        .where(
            func.char_length(lexemes.c.lexeme) > MIN_TERM_LENGTH,
            lexemes.c.lexeme.notin_(list(STOPWORDS)),
            ~lexemes.c.lexeme.op('~')(r'^\d+$'),
        )
        .group_by(lexemes.c.lexeme)
        .order_by(func.count().desc(), lexemes.c.lexeme)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).mappings().all()
    return [Term(term=row['lexeme'], frequency=row['n']) for row in rows]


# =========================================================================
# Indicadores
# =========================================================================


async def fetch_production_series(
    session: AsyncSession, kind: str, filters: ProductionBaseFilter
) -> list[SeriesPoint]:
    """Quantidade de produções por ano, com os filtros das listagens."""
    table = PRODUCTION_TABLES[kind]
    stmt = (
        select(table.c.year, func.count().label('n'))
        .where(
            table.c.year.isnot(None),
            *build_production_conditions(table, filters, frozenset()),
        )
        .group_by(table.c.year)
        .order_by(table.c.year)
    )
    rows = (await session.execute(stmt)).mappings().all()
    return [SeriesPoint(period=row['year'], value=row['n']) for row in rows]
