# ruff: noqa: PLR0913, PLR0917
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.graduate_program import GraduateProgramResearcher
from simcc.core.db.models.production import BibliographicProduction
from simcc.core.db.models.researcher import Researcher
from simcc.core.db.models.researcher_institution import ResearcherInstitution
from simcc.v2.schemas.filters import ResearcherFilter


def _build_filters(filters: ResearcherFilter) -> list:
    conditions = []

    if filters.q and filters.q.strip():
        conditions.append(Researcher.name.ilike(f'%{filters.q.strip()}%'))

    if filters.institution_id:
        sub_inst = select(ResearcherInstitution.researcher_id).where(
            ResearcherInstitution.institution_id == filters.institution_id
        )
        conditions.append(
            (Researcher.institution_id == filters.institution_id)
            | (Researcher.id.in_(sub_inst))
        )

    if filters.graduate_program_id:
        sub_gp = select(GraduateProgramResearcher.researcher_id).where(
            GraduateProgramResearcher.graduate_program_id
            == filters.graduate_program_id
        )
        conditions.append(Researcher.id.in_(sub_gp))

    if filters.year_start is not None or filters.year_end is not None:
        p_conds = []
        if filters.year_start is not None:
            p_conds.append(BibliographicProduction.year_ >= filters.year_start)
        if filters.year_end is not None:
            p_conds.append(BibliographicProduction.year_ <= filters.year_end)
        sub_bp = select(BibliographicProduction.researcher_id).where(
            and_(*p_conds)
        )
        conditions.append(Researcher.id.in_(sub_bp))

    return conditions


async def fetch_researchers(
    session: AsyncSession,
    filters: Optional[ResearcherFilter] = None,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = 'name',
    sort_order: str = 'asc',
) -> tuple[list[dict[str, Any]], int]:
    resolved_filters = filters or ResearcherFilter()
    conditions = _build_filters(resolved_filters)

    count_stmt = select(func.count(Researcher.id.distinct()))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total_items = (await session.execute(count_stmt)).scalar() or 0

    if total_items == 0:
        return [], 0

    stmt = select(Researcher.id.label('researcher_id'), Researcher.name)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    sort_col = getattr(Researcher, sort_by, Researcher.name)
    if str(sort_order).lower() == 'desc':
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())

    offset = max(0, (page - 1) * per_page)
    stmt = stmt.offset(offset).limit(per_page)

    result = await session.execute(stmt)
    rows = result.mappings().all()
    data = [
        {'researcher_id': row['researcher_id'], 'name': row['name']}
        for row in rows
    ]

    return data, total_items
