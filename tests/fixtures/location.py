import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.location import IdentityTerritory, Municipality
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


@pytest_asyncio.fixture
def geo_city(session: AsyncSession, city_factory):
    """Cidade com código IBGE ligada a um município e, se informado, a um
    território de identidade. Reaproveita território e município já
    criados no teste."""

    async def _create(  # noqa: PLR0913, PLR0917
        name: str,
        ibge_code: str,
        territory_code: int | None = None,
        territory_name: str | None = None,
        uf: str = 'BA',
        city_name: str | None = None,
    ):
        if territory_code is not None and (
            await session.get(IdentityTerritory, territory_code) is None
        ):
            session.add(
                IdentityTerritory(
                    code=territory_code,
                    name=territory_name or f'TERRITORIO {territory_code}',
                    slug=f'territorio-{territory_code}',
                )
            )
            await session.flush()
        if await session.get(Municipality, ibge_code) is None:
            session.add(
                Municipality(
                    ibge_code=ibge_code,
                    name=name,
                    uf=uf,
                    territory_code=territory_code,
                )
            )
            await session.flush()
        return await city_factory(name=city_name or name, ibge_code=ibge_code)

    return _create
