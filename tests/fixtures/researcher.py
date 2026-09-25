import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.services.mv_refresh_service import (
    refresh_search_materialized_views,
)
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
        await refresh_search_materialized_views(session, concurrently=False)
        return researcher

    return _create_researcher
