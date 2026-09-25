import factory

from simcc.core.db.models.researcher_institution import ResearcherInstitution


class ResearcherInstitutionFactory(factory.Factory):
    class Meta:
        model = ResearcherInstitution
