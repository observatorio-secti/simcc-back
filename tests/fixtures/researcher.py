import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.researcher import ResearcherFactory
from tests.factories.researcher_institution import (
    ResearcherInstitutionFactory,
)


@pytest_asyncio.fixture
def researcher_factory(session: AsyncSession, refresh_mvs):
    """Cria um pesquisador; `institution_id` vira um vínculo em
    `researcher_institution`, não a coluna legada."""

    async def _create_researcher(institution_id=None, **kwargs):
        researcher = ResearcherFactory(**kwargs)
        session.add(researcher)
        await session.flush()
        if institution_id is not None:
            session.add(
                ResearcherInstitutionFactory(
                    researcher_id=researcher.id,
                    institution_id=institution_id,
                )
            )
        await session.commit()
        await refresh_mvs()
        return researcher

    return _create_researcher


@pytest_asyncio.fixture
def researcher_institution_factory(session: AsyncSession, institution_factory):
    async def _create_researcher_institution(**kwargs):
        if 'institution_id' not in kwargs:
            institution = await institution_factory()
            kwargs['institution_id'] = institution.id

        link = ResearcherInstitutionFactory(**kwargs)
        session.add(link)
        await session.commit()
        return link

    return _create_researcher_institution
