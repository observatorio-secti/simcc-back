import uuid

import pytest

from simcc.core.db.models.graduate_program import GraduateProgram
from simcc.core.db.models.institution import JCR, PeriodicalMagazine
from simcc.core.db.models.openalex import OpenAlexArticle, OpenAlexResearcher
from simcc.core.db.models.production import (
    BibliographicProduction,
    BibliographicProductionArticle,
    Foment,
    Guidance,
    ParticipationEvents,
    Publishing,
    ResearchProject,
    ResearchReport,
    Software,
)
from simcc.core.db.models.researcher_institution import ResearcherInstitution
from simcc.data_consistency.metrics import (
    GLOBAL,
    INSTITUTION,
    get_graduate_programs_metrics,
    get_jcr_metrics,
    get_openalex_metrics,
    get_production_metrics,
    get_researchers_metrics,
    get_teachers_metrics,
)


@pytest.mark.asyncio
async def test_researcher_and_teacher_metrics_are_distinct_by_scope(
    session, institution_factory, researcher_factory
):
    first = await institution_factory(name='First University')
    second = await institution_factory(name='Second University')
    researcher = await researcher_factory(
        institution_id=first.id, status=True, docente=True
    )
    session.add(
        ResearcherInstitution(
            researcher_id=researcher.id,
            institution_id=second.id,
        )
    )
    await session.commit()
    await researcher_factory(
        institution_id=first.id, status=False, docente=True
    )

    researcher_metrics = await get_researchers_metrics(session)
    teacher_metrics = await get_teachers_metrics(session)

    assert [
        metric.value
        for metric in researcher_metrics
        if metric.scope == GLOBAL
    ] == [1]
    assert {
        metric.institution_name: metric.value
        for metric in researcher_metrics
        if metric.scope == INSTITUTION
    } == {'First University': 1, 'Second University': 1}
    assert [
        metric.value for metric in teacher_metrics if metric.scope == GLOBAL
    ] == [2]
    assert {
        metric.institution_name: metric.value
        for metric in teacher_metrics
        if metric.scope == INSTITUTION
    } == {'First University': 2, 'Second University': 1}


@pytest.mark.asyncio
async def test_graduate_program_metrics(session, institution_factory):
    institution = await institution_factory(name='Research University')
    session.add_all([
        GraduateProgram(
            name='Program one',
            area='Area',
            modality='ACADEMIC',
            institution_id=institution.id,
        ),
    ])
    await session.commit()

    program_metrics = await get_graduate_programs_metrics(session)

    assert [
        metric.value
        for metric in program_metrics
        if metric.scope == GLOBAL
    ] == [1]
    assert [
        metric.value
        for metric in program_metrics
        if metric.scope == INSTITUTION
    ] == [1]


@pytest.mark.asyncio
async def test_production_metrics_cover_listing_entities(
    session, institution_factory, researcher_factory
):
    institution = await institution_factory(name='Production University')
    researcher = await researcher_factory(
        institution_id=institution.id, status=True
    )
    session.add_all(
        [
            BibliographicProduction(
                title='Article',
                type='ARTICLE',
                researcher_id=researcher.id,
                sequence_code=1,
            ),
            BibliographicProduction(
                title='Book',
                type='BOOK',
                researcher_id=researcher.id,
                sequence_code=2,
            ),
            Software(researcher_id=researcher.id, sequence_code=3),
            ResearchReport(researcher_id=researcher.id, sequence_code=4),
            Guidance(researcher_id=researcher.id, sequence_code=5),
            ParticipationEvents(
                researcher_id=researcher.id, sequence_code=6
            ),
            ResearchProject(researcher_id=researcher.id, sequence_code=7),
            Publishing(
                title='Magazine text',
                researcher_id=researcher.id,
                sequence_code=8,
            ),
            Foment(
                researcher_id=researcher.id,
                sequence_code=9,
                institute_name='CNPq',
                scholarship_quantity=1,
            ),
            PeriodicalMagazine(name='Journal'),
        ]
    )
    await session.commit()

    metrics = await get_production_metrics(session)
    global_values = {
        metric.metric_key: metric.value
        for metric in metrics
        if metric.scope == GLOBAL
    }
    institution_values = {
        metric.metric_key: metric.value
        for metric in metrics
        if metric.scope == INSTITUTION
    }

    assert global_values['articles_total'] == 1
    assert global_values['books_total'] == 1
    assert global_values['softwares_total'] == 1
    assert global_values['technical_reports_total'] == 1
    assert global_values['guidance_total'] == 1
    assert global_values['event_participation_total'] == 1
    assert global_values['research_projects_total'] == 1
    assert global_values['publishing_total'] == 1
    assert global_values['cnpq_fellows_total'] == 1
    assert global_values['periodicals_total'] == 1
    assert institution_values['articles_total'] == 1
    assert institution_values['cnpq_fellows_total'] == 1


@pytest.mark.asyncio
async def test_jcr_and_openalex_metrics_use_global_and_institution_scopes(
    session, institution_factory, researcher_factory
):
    jcr_citations = 25
    jcr_articles = 100
    openalex_works = 40
    openalex_citations = 120
    openalex_i10 = 5
    article_citations = 12
    institution = await institution_factory(name='Bibliometric University')
    researcher = await researcher_factory(
        institution_id=institution.id, status=True
    )
    article = BibliographicProduction(
        title='JCR Article',
        type='ARTICLE',
        researcher_id=researcher.id,
        sequence_code=20,
    )
    periodical = PeriodicalMagazine(name='JCR Magazine')
    session.add_all([article, periodical])
    await session.flush()
    session.add_all(
        [
            JCR(
                journalname='JCR Journal',
                totalcites=str(jcr_citations),
                totalarticles=str(jcr_articles),
                jif2019=3.2,
            ),
            BibliographicProductionArticle(
                bibliographic_production_id=article.id,
                periodical_magazine_id=periodical.id,
                jcr='3.2',
            ),
            OpenAlexResearcher(
                researcher_id=researcher.id,
                h_index=7,
                works_count=openalex_works,
                cited_by_count=openalex_citations,
                i10_index=openalex_i10,
            ),
            OpenAlexArticle(
                article_id=article.id,
                id=uuid.uuid4(),
                citations_count=article_citations,
            ),
        ]
    )
    await session.commit()

    jcr_metrics = await get_jcr_metrics(session)
    openalex_metrics = await get_openalex_metrics(session)

    jcr_global = {
        metric.metric_key: metric.value for metric in jcr_metrics
    }
    openalex_global = {
        metric.metric_key: metric.value
        for metric in openalex_metrics
        if metric.scope == GLOBAL
    }
    openalex_institution = {
        metric.metric_key: metric.value
        for metric in openalex_metrics
        if metric.scope == INSTITUTION
    }

    assert jcr_global['jcr_records_total'] == 1
    assert jcr_global['jcr_articles_total'] == 1
    assert jcr_global['jcr_citations_total'] == jcr_citations
    assert jcr_global['jcr_journal_articles_total'] == jcr_articles
    assert openalex_global['openalex_profiles_total'] == 1
    assert openalex_global['openalex_works_total'] == openalex_works
    assert (
        openalex_global['openalex_researcher_citations_total']
        == openalex_citations
    )
    assert openalex_global['openalex_i10_total'] == openalex_i10
    assert openalex_global['openalex_articles_total'] == 1
    assert openalex_institution['openalex_profiles_total'] == 1
    assert openalex_institution['openalex_articles_total'] == 1
    assert (
        openalex_institution['openalex_article_citations_total']
        == article_citations
    )
