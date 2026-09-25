"""Repositório do perfil individual de pesquisador v2 (tabelas base)."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.graduate_program import (
    GraduateProgram,
    GraduateProgramResearcher,
)
from simcc.core.db.models.openalex import OpenAlexResearcher
from simcc.core.db.models.research_group import (
    ResearchGroup,
    ResearchGroupResearcher,
)
from simcc.core.db.models.researcher import (
    Researcher,
    ResearcherProduction,
)
from simcc.v2.schemas.graduate_program import GraduateProgramRef
from simcc.v2.schemas.research_group import ResearchGroupRef
from simcc.v2.schemas.researcher import (
    Bibliometrics,
    GraduateProgramLink,
    ResearcherCounts,
    ResearcherDetail,
    ResearcherIdentifiers,
    researcher_image_url,
)


async def fetch_researcher_profile(
    session: AsyncSession,
    researcher_id: UUID,
) -> Optional[ResearcherDetail]:
    """Busca os dados escalares do perfil, sem as coleções."""
    r = Researcher
    rp = ResearcherProduction
    opr = OpenAlexResearcher
    stmt = (
        select(
            r.id,
            r.name,
            r.graduation,
            r.classification,
            r.last_update,
            r.abstract,
            r.abstract_ai,
            r.lattes_id,
            r.lattes_10_id,
            r.orcid,
            func.coalesce(rp.articles, 0).label('articles'),
            func.coalesce(rp.book_chapters, 0).label('book_chapters'),
            func.coalesce(rp.book, 0).label('books'),
            func.coalesce(rp.patent, 0).label('patents'),
            func.coalesce(rp.software, 0).label('software'),
            func.coalesce(rp.brand, 0).label('brands'),
            opr.researcher_id.label('openalex_researcher_id'),
            opr.scopus,
            opr.openalex,
            opr.h_index,
            opr.i10_index,
            opr.cited_by_count,
            opr.works_count,
        )
        .outerjoin(rp, rp.researcher_id == r.id)
        .outerjoin(opr, opr.researcher_id == r.id)
        .where(r.id == researcher_id)
    )
    row = (await session.execute(stmt)).mappings().one_or_none()
    if row is None:
        return None

    bibliometrics = None
    if row['openalex_researcher_id'] is not None:
        bibliometrics = Bibliometrics.model_validate(dict(row))

    return ResearcherDetail(
        researcher_id=row['id'],
        name=row['name'],
        image=researcher_image_url(row['id']),
        graduation=row['graduation'],
        classification=row['classification'],
        lattes_update=row['last_update'],
        counts=ResearcherCounts.model_validate(dict(row)),
        abstract=row['abstract'],
        abstract_ai=row['abstract_ai'],
        identifiers=ResearcherIdentifiers.model_validate(dict(row)),
        bibliometrics=bibliometrics,
    )


async def fetch_graduate_programs(
    session: AsyncSession,
    researcher_id: UUID,
) -> list[GraduateProgramLink]:
    """Busca os programas de pós-graduação do pesquisador."""
    gp = GraduateProgram
    gpr = GraduateProgramResearcher
    stmt = (
        select(gp.graduate_program_id, gp.name, gp.acronym, gpr.type_)
        .join(gpr, gpr.graduate_program_id == gp.graduate_program_id)
        .where(gpr.researcher_id == researcher_id)
        .order_by(gp.name.asc(), gp.graduate_program_id.asc())
    )
    rows = (await session.execute(stmt)).mappings().all()
    return [
        GraduateProgramLink(
            program=GraduateProgramRef(
                id=row['graduate_program_id'],
                name=row['name'],
                acronym=row['acronym'],
            ),
            type=row['type_'],
        )
        for row in rows
    ]


async def fetch_research_groups(
    session: AsyncSession,
    researcher_id: UUID,
) -> list[ResearchGroupRef]:
    """Busca os grupos de pesquisa do pesquisador."""
    rg = ResearchGroup
    rgr = ResearchGroupResearcher
    stmt = (
        select(rg.id, rg.name)
        .join(rgr, rgr.research_group_id == rg.id)
        .where(rgr.researcher_id == researcher_id)
        .order_by(rg.name.asc(), rg.id.asc())
    )
    rows = (await session.execute(stmt)).mappings().all()
    return [ResearchGroupRef(id=row['id'], name=row['name']) for row in rows]
