import itertools
import uuid

import factory

from simcc.core.db.models.institution import PeriodicalMagazine
from simcc.core.db.models.openalex import OpenAlexArticle
from simcc.core.db.models.production import (
    BibliographicProduction,
    BibliographicProductionArticle,
    Software,
)

_sequence_codes = itertools.count(1)


def next_sequence_code() -> int:
    """Código de sequência (SEQUENCIA-PRODUCAO do Lattes) único para cada
    produção criada nos testes."""
    return next(_sequence_codes)


class BibliographicProductionFactory(factory.Factory):
    class Meta:
        model = BibliographicProduction

    title = factory.Faker('sentence')
    sequence_code = factory.LazyFunction(next_sequence_code)
    type = 'ARTICLE'
    year = '2024'
    year_ = 2024


class SoftwareFactory(factory.Factory):
    class Meta:
        model = Software

    title = factory.Faker('sentence')
    sequence_code = factory.LazyFunction(next_sequence_code)
    year = 2022


class PeriodicalMagazineFactory(factory.Factory):
    class Meta:
        model = PeriodicalMagazine

    name = factory.Sequence(lambda n: f'Revista {n}')


class BibliographicProductionArticleFactory(factory.Factory):
    class Meta:
        model = BibliographicProductionArticle

    periodical_magazine_name = 'Revista Teste'
    qualis = 'A1'


class OpenAlexArticleFactory(factory.Factory):
    class Meta:
        model = OpenAlexArticle

    id = factory.LazyFunction(uuid.uuid4)
    abstract = factory.Faker('paragraph')
