import factory

from simcc.core.db.models.location import City, Country


class CountryFactory(factory.Factory):
    class Meta:
        model = Country

    name = factory.Sequence(lambda n: f'Country {n}')
    name_pt = factory.Sequence(lambda n: f'País {n}')


class CityFactory(factory.Factory):
    class Meta:
        model = City

    name = factory.Sequence(lambda n: f'City {n}')
