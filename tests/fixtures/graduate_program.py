import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.graduate_program import GraduateProgramFactory
from tests.factories.institution import InstitutionFactory


@pytest_asyncio.fixture
def graduate_program_factory(session: AsyncSession):
    async def _create_graduate_program(**kwargs):
        if 'institution_id' not in kwargs:
            inst = InstitutionFactory()
            session.add(inst)
            await session.flush()
            kwargs['institution_id'] = inst.id
        gp = GraduateProgramFactory(**kwargs)
        session.add(gp)
        await session.commit()
        return gp

    return _create_graduate_program
