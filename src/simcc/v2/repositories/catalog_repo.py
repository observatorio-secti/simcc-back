"""Repositório para consulta de catálogos (instituições e programas)."""

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.graduate_program import GraduateProgram
from simcc.core.db.models.institution import Institution
from simcc.v2.schemas.catalog import CatalogItem
from simcc.v2.schemas.params import PaginationParams


async def fetch_institutions(
    session: AsyncSession,
    q: Optional[str] = None,
    pagination: Optional[PaginationParams] = None,
) -> tuple[list[CatalogItem], int]:
    """Retorna lista paginada e total de instituições cadastradas."""
    pag = pagination or PaginationParams()
    cond = None
    if q and q.strip():
        term = f'%{q.strip()}%'
        cond = or_(
            Institution.name.ilike(term),
            Institution.acronym.ilike(term),
        )

    count_stmt = select(func.count(Institution.id))
    if cond is not None:
        count_stmt = count_stmt.where(cond)
    total_items = (await session.execute(count_stmt)).scalar() or 0

    if total_items == 0:
        return [], 0

    offset = max(0, (pag.page - 1) * pag.per_page)
    data_stmt = (
        select(
            Institution.id,
            Institution.name,
            Institution.acronym,
        )
        .order_by(Institution.name.asc(), Institution.id.asc())
        .offset(offset)
        .limit(pag.per_page)
    )
    if cond is not None:
        data_stmt = data_stmt.where(cond)

    rows = (await session.execute(data_stmt)).mappings().all()
    items = [
        CatalogItem(
            id=row['id'],
            name=row['name'],
            acronym=row['acronym'],
        )
        for row in rows
    ]
    return items, total_items


async def fetch_graduate_programs(
    session: AsyncSession,
    q: Optional[str] = None,
    pagination: Optional[PaginationParams] = None,
) -> tuple[list[CatalogItem], int]:
    """Retorna lista paginada e total de programas de pós-graduação."""
    pag = pagination or PaginationParams()
    cond = None
    if q and q.strip():
        term = f'%{q.strip()}%'
        cond = or_(
            GraduateProgram.name.ilike(term),
            GraduateProgram.acronym.ilike(term),
        )

    count_stmt = select(func.count(GraduateProgram.graduate_program_id))
    if cond is not None:
        count_stmt = count_stmt.where(cond)
    total_items = (await session.execute(count_stmt)).scalar() or 0

    if total_items == 0:
        return [], 0

    offset = max(0, (pag.page - 1) * pag.per_page)
    data_stmt = (
        select(
            GraduateProgram.graduate_program_id.label('id'),
            GraduateProgram.name,
            GraduateProgram.acronym,
        )
        .order_by(
            GraduateProgram.name.asc(),
            GraduateProgram.graduate_program_id.asc(),
        )
        .offset(offset)
        .limit(pag.per_page)
    )
    if cond is not None:
        data_stmt = data_stmt.where(cond)

    rows = (await session.execute(data_stmt)).mappings().all()
    items = [
        CatalogItem(
            id=row['id'],
            name=row['name'],
            acronym=row['acronym'],
        )
        for row in rows
    ]
    return items, total_items
