import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.location import CityFactory, CountryFactory


@pytest_asyncio.fixture
def city_factory(session: AsyncSession):
    async def _create_city(**kwargs):
        if 'country_id' not in kwargs:
            country = CountryFactory()
            session.add(country)
            await session.flush()
            kwargs['country_id'] = country.id
        city = CityFactory(**kwargs)
        session.add(city)
        await session.commit()
        return city

    return _create_city
