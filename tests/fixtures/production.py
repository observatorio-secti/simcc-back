import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.institution import PeriodicalMagazine
from simcc.core.db.models.openalex import OpenAlexArticle
from simcc.core.db.models.production import (
    BibliographicProduction,
    BibliographicProductionArticle,
    Software,
)


@pytest_asyncio.fixture
def production_factory(session: AsyncSession, refresh_mvs):
    """Cria uma produção genérica (ex: livro, software, artigo) e
    atualiza as MVs."""

    async def _create(researcher, title, type_='ARTICLE', year=2022, **kwargs):
        if type_ == 'SOFTWARE':
            production = Software(
                researcher_id=researcher.id, title=title, year=year, **kwargs
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
