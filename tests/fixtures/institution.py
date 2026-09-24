import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.institution import InstitutionFactory


@pytest_asyncio.fixture
def institution_factory(session: AsyncSession):
    async def _create_institution(**kwargs):
        institution = InstitutionFactory(**kwargs)
        session.add(institution)
        await session.commit()
        return institution

    return _create_institution
