import factory

from simcc.core.db.models.graduate_program import GraduateProgram


class GraduateProgramFactory(factory.Factory):
    class Meta:
        model = GraduateProgram

    name = factory.Sequence(lambda n: f'Graduate Program {n}')
    area = 'Ciência da Computação'
    modality = 'Acadêmico'
    acronym = factory.Sequence(lambda n: f'GP{n}')
