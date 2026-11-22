"""Repositório dos catálogos v2: instituições e programas de pós-graduação."""

from typing import Optional
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, or_, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.graduate_program import (
    GraduateProgram,
    GraduateProgramResearcher,
    ResearchLinesPrograms,
)
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.miscellaneous import Labs
from simcc.core.db.models.production import Foment
from simcc.core.db.models.research_group import ResearchGroup
from simcc.core.db.models.researcher_institution import ResearcherInstitution
from simcc.v2.repositories.researcher_facets_repo import rank_facet_values
from simcc.v2.schemas.catalog import (
    CatalogSort,
    GraduateProgramDetail,
    GraduateProgramFilter,
    GraduateProgramSummary,
    InstitutionCounts,
    InstitutionDetail,
    InstitutionFilter,
    ResearchLine,
    ScholarshipBreakdownItem,
)
from simcc.v2.schemas.institution import InstitutionRef
from simcc.v2.schemas.params import PaginationParams
from simcc.v2.schemas.researcher import FacetResult

GP = GraduateProgram


def _text_match(q: Optional[str], *columns) -> Optional[ColumnElement]:
    if not q or not q.strip():
        return None
    term = f'%{q.strip()}%'
    return or_(*(col.ilike(term) for col in columns))


def _order(sort: CatalogSort, name_col, acronym_col, id_col) -> list:
    col = acronym_col if sort.sort_by == 'acronym' else name_col
    ordered = col.desc() if sort.sort_order == 'desc' else col.asc()
    return [ordered.nulls_last(), id_col.asc()]


async def _paginate(
    session: AsyncSession,
    stmt: Select,
    count_stmt: Select,
    pagination: PaginationParams,
):
    total_items = (await session.execute(count_stmt)).scalar() or 0
    if total_items == 0:
        return [], 0
    offset = max(0, (pagination.page - 1) * pagination.per_page)
    rows = (
        (await session.execute(stmt.offset(offset).limit(pagination.per_page)))
        .mappings()
        .all()
    )
    return rows, total_items


# =========================================================================
# Instituições
# =========================================================================


async def fetch_institutions(
    session: AsyncSession,
    filters: Optional[InstitutionFilter] = None,
    pagination: Optional[PaginationParams] = None,
    sort: Optional[CatalogSort] = None,
) -> tuple[list[InstitutionRef], int]:
    """Lista paginada e total de instituições cadastradas com acrônimo."""
    filters = filters or InstitutionFilter()
    pagination = pagination or PaginationParams()
    sort = sort or CatalogSort()
    conditions = [
        Institution.acronym.is_not(None),
        func.length(func.trim(Institution.acronym)) > 0,
    ]
    cond = _text_match(filters.q, Institution.name, Institution.acronym)
    if cond is not None:
        conditions.append(cond)

    order_cols = _order(
        sort, Institution.name, Institution.acronym, Institution.id
    )
    stmt = (
        select(
            Institution.id,
            Institution.name,
            Institution.acronym,
            Institution.image,
        )
        .where(*conditions)
        .order_by(*order_cols)
    )
    count_stmt = select(func.count(Institution.id)).where(*conditions)

    rows, total = await _paginate(session, stmt, count_stmt, pagination)
    return [InstitutionRef.from_row(row) for row in rows], total


async def _fetch_institution_scholarships(
    session: AsyncSession, institution_id: UUID
) -> tuple[int, list[ScholarshipBreakdownItem]]:
    """Total distinto de bolsistas e detalhamento por modalidade/nível."""
    total_holders = (
        await session.execute(
            select(func.count(func.distinct(Foment.researcher_id)))
            .join(
                ResearcherInstitution,
                ResearcherInstitution.researcher_id == Foment.researcher_id,
            )
            .where(ResearcherInstitution.institution_id == institution_id)
        )
    ).scalar() or 0

    if total_holders == 0:
        return 0, []

    count_expr = func.count(func.distinct(Foment.researcher_id))
    ri_join_cond = ResearcherInstitution.researcher_id == Foment.researcher_id
    rows = (
        (
            await session.execute(
                select(
                    Foment.modality_name.label('modality'),
                    Foment.category_level_code.label('category_level'),
                    count_expr.label('researchers'),
                )
                .join(ResearcherInstitution, ri_join_cond)
                .where(ResearcherInstitution.institution_id == institution_id)
                .group_by(Foment.modality_name, Foment.category_level_code)
                .order_by(
                    count_expr.desc(),
                    Foment.modality_name.asc().nulls_last(),
                    Foment.category_level_code.asc().nulls_last(),
                )
            )
        )
        .mappings()
        .all()
    )
    breakdown = [
        ScholarshipBreakdownItem(
            modality=row['modality'],
            category_level=row['category_level'],
            researchers=row['researchers'],
        )
        for row in rows
    ]
    return total_holders, breakdown


async def _fetch_institution_research_groups_count(
    session: AsyncSession, institution_id: UUID
) -> int:
    """Conta grupos de pesquisa cujos líderes são vinculados à instituição."""
    inst_researchers = (
        select(ResearcherInstitution.researcher_id)
        .where(ResearcherInstitution.institution_id == institution_id)
        .cte('inst_researchers')
    )
    by_first = select(ResearchGroup.id).join(
        inst_researchers,
        ResearchGroup.first_leader_id == inst_researchers.c.researcher_id,
    )
    by_second = select(ResearchGroup.id).join(
        inst_researchers,
        ResearchGroup.second_leader_id == inst_researchers.c.researcher_id,
    )
    groups_union = union(by_first, by_second).subquery()
    return (
        await session.execute(select(func.count()).select_from(groups_union))
    ).scalar() or 0


async def _fetch_institution_labs_count(
    session: AsyncSession, institution_id: UUID
) -> int:
    """Conta laboratórios vinculados diretamente à instituição."""
    return (
        await session.execute(
            select(func.count(Labs.id)).where(
                Labs.institution_id == institution_id
            )
        )
    ).scalar() or 0


async def fetch_institution(
    session: AsyncSession, institution_id: UUID
) -> Optional[InstitutionDetail]:
    """Detalhe da instituição com contagens e bolsistas, ou None."""
    row = (
        (
            await session.execute(
                select(
                    Institution.id,
                    Institution.name,
                    Institution.acronym,
                    Institution.image,
                    Institution.description,
                    Institution.lattes_id,
                    Institution.latitude,
                    Institution.longitude,
                ).where(Institution.id == institution_id)
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return None

    researchers = (
        await session.execute(
            select(
                func.count(func.distinct(ResearcherInstitution.researcher_id))
            ).where(ResearcherInstitution.institution_id == institution_id)
        )
    ).scalar() or 0
    programs = (
        await session.execute(
            select(func.count(GP.graduate_program_id)).where(
                GP.institution_id == institution_id
            )
        )
    ).scalar() or 0
    scholarship_holders, scholarships = await _fetch_institution_scholarships(
        session, institution_id
    )
    research_groups = await _fetch_institution_research_groups_count(
        session, institution_id
    )
    labs = await _fetch_institution_labs_count(session, institution_id)

    ref = InstitutionRef.from_row(row)
    return InstitutionDetail(
        **ref.model_dump(),
        description=row['description'],
        lattes_id=row['lattes_id'],
        latitude=row['latitude'],
        longitude=row['longitude'],
        counts=InstitutionCounts(
            researchers=researchers,
            graduate_programs=programs,
            scholarship_holders=scholarship_holders,
            research_groups=research_groups,
            labs=labs,
        ),
        scholarships=scholarships,
    )


# =========================================================================
# Programas de pós-graduação
# =========================================================================

# Filtro de lista → coluna do programa
_GP_COLUMNS = {
    'institution_id': GP.institution_id,
    'area': GP.area,
    'modality': GP.modality,
    'rating': GP.rating,
    'state': GP.state,
    'city': GP.city,
}

# Nome da faceta → campo de filtro em GraduateProgramFilter (quando difere)
_GP_FACET_PARAMS = {'institution': 'institution_id'}


def _gp_conditions(
    filters: GraduateProgramFilter, exclude: frozenset[str] = frozenset()
) -> list[ColumnElement]:
    conditions = []
    text_cond = _text_match(filters.q, GP.name, GP.acronym)
    if text_cond is not None:
        conditions.append(text_cond)
    for field, column in _GP_COLUMNS.items():
        values = getattr(filters, field)
        if values and field not in exclude:
            conditions.append(column.in_(values))
    return conditions


def _gp_summary(row) -> GraduateProgramSummary:
    return GraduateProgramSummary(
        id=row['id'],
        name=row['name'],
        acronym=row['acronym'],
        institution_id=row['institution_id'],
        area=row['area'],
        modality=row['modality'],
        rating=row['rating'],
        state=row['state'],
        city=row['city'],
    )


_GP_SUMMARY_COLUMNS = (
    GP.graduate_program_id.label('id'),
    GP.name,
    GP.acronym,
    GP.institution_id,
    GP.area,
    GP.modality,
    GP.rating,
    GP.state,
    GP.city,
)


async def fetch_graduate_programs(
    session: AsyncSession,
    filters: Optional[GraduateProgramFilter] = None,
    pagination: Optional[PaginationParams] = None,
    sort: Optional[CatalogSort] = None,
) -> tuple[list[GraduateProgramSummary], int]:
    """Lista paginada e total de programas de pós-graduação."""
    filters = filters or GraduateProgramFilter()
    pagination = pagination or PaginationParams()
    sort = sort or CatalogSort()
    conditions = _gp_conditions(filters)

    stmt = (
        select(*_GP_SUMMARY_COLUMNS)
        .where(*conditions)
        .order_by(*_order(sort, GP.name, GP.acronym, GP.graduate_program_id))
    )
    count_stmt = select(func.count(GP.graduate_program_id)).where(*conditions)
    rows, total = await _paginate(session, stmt, count_stmt, pagination)
    return [_gp_summary(row) for row in rows], total


async def fetch_graduate_program_facets(
    session: AsyncSession,
    filters: GraduateProgramFilter,
    requested_facets: list[str],
    limit: int,
) -> dict[str, FacetResult]:
    """Facetas disjuntivas: cada uma ignora o próprio filtro."""
    facets = {}
    for name in requested_facets:
        field = _GP_FACET_PARAMS.get(name, name)
        column = _GP_COLUMNS[field]
        pairs = select(GP.graduate_program_id, column.label('value')).where(
            column.isnot(None), *_gp_conditions(filters, frozenset({field}))
        )
        selected = getattr(filters, field)
        if name == 'institution':
            facet = await rank_facet_values(
                session,
                pairs,
                selected=selected,
                limit=limit,
                entity=Institution,
                entity_id=Institution.id,
            )
        else:
            facet = await rank_facet_values(
                session, pairs, selected=selected, limit=limit
            )
        facet.param = field
        facets[name] = facet
    return facets


async def fetch_graduate_program(
    session: AsyncSession, program_id: UUID
) -> Optional[GraduateProgramDetail]:
    """Detalhe do programa com linhas de pesquisa, ou None."""
    row = (
        (
            await session.execute(
                select(
                    *_GP_SUMMARY_COLUMNS,
                    GP.code,
                    GP.name_en,
                    GP.type,
                    GP.description,
                    GP.site,
                    GP.coordinator,
                    GP.email,
                    GP.phone,
                    GP.start,
                ).where(GP.graduate_program_id == program_id)
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return None

    lines = (
        (
            await session.execute(
                select(
                    ResearchLinesPrograms.name,
                    ResearchLinesPrograms.area,
                    ResearchLinesPrograms.start_year,
                    ResearchLinesPrograms.end_year,
                )
                .where(ResearchLinesPrograms.graduate_program_id == program_id)
                .order_by(ResearchLinesPrograms.name)
            )
        )
        .mappings()
        .all()
    )
    researchers = (
        await session.execute(
            select(
                func.count(
                    func.distinct(GraduateProgramResearcher.researcher_id)
                )
            ).where(
                GraduateProgramResearcher.graduate_program_id == program_id
            )
        )
    ).scalar() or 0

    institution = None
    if row['institution_id'] is not None:
        inst_row = (
            (
                await session.execute(
                    select(
                        Institution.id,
                        Institution.name,
                        Institution.acronym,
                        Institution.image,
                    ).where(Institution.id == row['institution_id'])
                )
            )
            .mappings()
            .first()
        )
        if inst_row is not None:
            institution = InstitutionRef.from_row(inst_row)

    summary = _gp_summary(row)
    return GraduateProgramDetail(
        **summary.model_dump(),
        institution=institution,
        code=row['code'],
        name_en=row['name_en'],
        type=row['type'],
        description=row['description'],
        site=row['site'],
        coordinator=row['coordinator'],
        email=row['email'],
        phone=row['phone'],
        start=row['start'],
        research_lines=[ResearchLine(**dict(line)) for line in lines],
        counts={'researchers': researchers},
    )
