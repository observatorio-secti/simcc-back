import factory

from simcc.core.db.models.researcher import Researcher


class ResearcherFactory(factory.Factory):
    class Meta:
        model = Researcher

    name = factory.Faker('name')
    lattes_id = factory.Sequence(lambda n: f'{n:016d}')
