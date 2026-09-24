import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.researcher import ResearcherFactory


@pytest_asyncio.fixture
def researcher_factory(session: AsyncSession, institution_factory):
    async def _create_researcher(**kwargs):
        if 'institution_id' not in kwargs:
            institution = await institution_factory()
            kwargs['institution_id'] = institution.id

        researcher = ResearcherFactory(**kwargs)
        session.add(researcher)
        await session.commit()
        return researcher

    return _create_researcher
