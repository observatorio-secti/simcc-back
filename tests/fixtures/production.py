import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.expertise import (
    AreaExpertise,
    AreaSpecialty,
    SubAreaExpertise,
)
from simcc.core.db.models.institution import PeriodicalMagazine
from simcc.core.db.models.openalex import OpenAlexArticle
from simcc.core.db.models.production import (
    BibliographicProduction,
    BibliographicProductionArticle,
    ParticipationEvents,
    Software,
)
from simcc.core.db.models.researcher import ResearcherAreaExpertise
from tests.factories.production import next_sequence_code


@pytest_asyncio.fixture
def production_factory(session: AsyncSession, refresh_mvs):
    """Cria uma produção genérica (ex: livro, software, artigo, evento) e
    atualiza as MVs."""

    async def _create(researcher, title, type_='ARTICLE', year=2022, **kwargs):
        kwargs.setdefault('sequence_code', next_sequence_code())
        if type_ == 'SOFTWARE':
            production = Software(
                researcher_id=researcher.id, title=title, year=year, **kwargs
            )
        elif type_ in ('PARTICIPATION_EVENT', 'EVENT'):
            production = ParticipationEvents(
                researcher_id=researcher.id,
                event_name=title,
                title=kwargs.pop('event_title', None),
                year=year,
                **kwargs,
            )
        else:
            production = BibliographicProduction(
                researcher_id=researcher.id,
                title=title,
                type=type_,
                year=str(year),
                year_=year,
                **kwargs,
            )
        session.add(production)
        await session.commit()
        await refresh_mvs()
        return production

    return _create


@pytest_asyncio.fixture
def area_specialty_factory(session: AsyncSession, refresh_mvs):
    """Cria uma especialidade de área vinculada ao pesquisador."""

    async def _create(researcher, name='Inteligência Artificial'):
        area_exp = AreaExpertise(name='Ciência da Computação')
        session.add(area_exp)
        await session.flush()

        sub = SubAreaExpertise(
            name='Metodologia e Técnicas da Computação',
            area_expertise_id=area_exp.id,
        )
        session.add(sub)
        await session.flush()

        area = AreaSpecialty(name=name, sub_area_expertise_id=sub.id)
        session.add(area)
        await session.flush()

        link = ResearcherAreaExpertise(
            researcher_id=researcher.id,
            sub_area_expertise_id=sub.id,
            area_specialty_id=area.id,
            area_expertise_id=area_exp.id,
        )
        session.add(link)
        await session.commit()
        await refresh_mvs()
        return area

    return _create


@pytest_asyncio.fixture
def article_factory(session: AsyncSession, refresh_mvs):
    """Cria um artigo completo (com revista, artigo de produção e
    opcionalmente resumo OpenAlex)."""

    async def _create(  # noqa: PLR0913, PLR0917
        researcher,
        title,
        abstract=None,
        type_='ARTICLE',
        year=2024,
        qualis='A1',
        magazine_name='Revista Teste',
        **kwargs,
    ):
        kwargs.setdefault('sequence_code', next_sequence_code())
        production = BibliographicProduction(
            title=title,
            type=type_,
            researcher_id=researcher.id,
            year=str(year),
            year_=int(year),
            **kwargs,
        )
        session.add(production)
        await session.flush()

        if type_ == 'ARTICLE':
            magazine = PeriodicalMagazine(name=magazine_name)
            session.add(magazine)
            await session.flush()
            session.add(
                BibliographicProductionArticle(
                    bibliographic_production_id=production.id,
                    periodical_magazine_id=magazine.id,
                    periodical_magazine_name=magazine_name,
                    qualis=qualis,
                )
            )

        if abstract is not None:
            session.add(
                OpenAlexArticle(
                    id=uuid.uuid4(),
                    article_id=production.id,
                    abstract=abstract,
                )
            )

        await session.commit()
        await refresh_mvs()
        return production

    return _create
