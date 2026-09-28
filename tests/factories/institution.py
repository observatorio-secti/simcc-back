import factory

from simcc.core.db.models.institution import Institution


class InstitutionFactory(factory.Factory):
    class Meta:
        model = Institution

    name = factory.Sequence(lambda n: f'Institution {n}')
    acronym = factory.Sequence(lambda n: f'INST{n}')
    description = factory.Faker('sentence')
