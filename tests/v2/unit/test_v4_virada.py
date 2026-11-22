from http import HTTPStatus
from uuid import uuid4

import pytest
from sqlalchemy import text

from simcc.core.db.models.graduate_program import GraduateProgramResearcher
from simcc.core.db.models.institution import PeriodicalMagazine
from simcc.core.db.models.production import Foment
from simcc.core.db.models.researcher_institution import ResearcherInstitution


@pytest.mark.asyncio
async def test_researcher_search_in_name_and_abstract(
    client, researcher_factory
):
    r_name = await researcher_factory(
        name='Helena Quantum', abstract='Estuda biologia marinha'
    )
    r_abs = await researcher_factory(
        name='Carlos Silva', abstract='Pesquisa em quantum computing'
    )

    by_name = client.get('/v2/researcher?q=quantum&search_in=name').json()
    assert [item['id'] for item in by_name['data']] == [str(r_name.id)]

    by_abs = client.get('/v2/researcher?q=quantum&search_in=abstract').json()
    assert [item['id'] for item in by_abs['data']] == [str(r_abs.id)]

    by_all = client.get('/v2/researcher?q=quantum&search_in=all').json()
    assert {item['id'] for item in by_all['data']} == {
        str(r_name.id),
        str(r_abs.id),
    }


@pytest.mark.asyncio
async def test_scholarship_institution_and_graduate_program_facets(
    client,
    session,
    researcher_factory,
    institution_factory,
    graduate_program_factory,
):
    inst = await institution_factory(name='UFBA', acronym='UFBA')
    gp = await graduate_program_factory(
        name='PGCOMP', acronym='PGCOMP', institution_id=inst.id
    )
    r = await researcher_factory(name='Bolsista Teste')
    session.add(
        ResearcherInstitution(researcher_id=r.id, institution_id=inst.id)
    )
    session.add(
        GraduateProgramResearcher(
            graduate_program_id=gp.graduate_program_id,
            researcher_id=r.id,
            year=2025,
            type_='PERMANENTE',
        )
    )
    session.add(
        Foment(
            researcher_id=r.id,
            sequence_code=1,
            modality_code='PQ',
            modality_name='Produtividade em Pesquisa',
            category_level_code='1A',
            call_title='Chamada 2025',
            aid_quantity=0,
            scholarship_quantity=1,
        )
    )
    await session.commit()

    res = client.get(
        '/v2/scholarship?facets=institution,graduate_program'
    )
    assert res.status_code == HTTPStatus.OK, res.text
    facets = res.json()['facets']
    assert facets['institution']['param'] == 'institution_id'
    assert facets['institution']['items'][0]['value'] == str(inst.id)
    assert facets['graduate_program']['param'] == 'graduate_program_id'
    assert facets['graduate_program']['items'][0]['value'] == str(
        gp.graduate_program_id
    )


@pytest.mark.asyncio
async def test_magazine_null_and_empty_qualis_treated_as_not_rated(
    client, session
):
    m_null = PeriodicalMagazine(
        name='Revista Sem Qualis Null', issn='1111-1111', qualis=None
    )
    m_empty = PeriodicalMagazine(
        name='Revista Sem Qualis Vazia', issn='2222-2222', qualis='  '
    )
    m_a1 = PeriodicalMagazine(
        name='Revista A1', issn='3333-3333', qualis='A1'
    )
    session.add_all([m_null, m_empty, m_a1])
    await session.commit()

    res = client.get('/v2/magazine?qualis=not_rated&facets=qualis')
    assert res.status_code == HTTPStatus.OK, res.text
    body = res.json()
    assert {item['issn'] for item in body['data']} == {
        '1111-1111',
        '2222-2222',
    }
    assert all(item['qualis'] is None for item in body['data'])
    assert all(item['qualis_status'] == 'not_rated' for item in body['data'])

    facet_values = {
        item['value']: item['count'] for item in body['facets']['qualis']['items']
    }
    assert facet_values['not_rated'] == 2
    assert facet_values['A1'] == 1


@pytest.mark.asyncio
async def test_magazine_text_and_event_work_routes(
    client, session, researcher_factory
):
    r = await researcher_factory(name='Autor Producao')
    bp_mag_id = uuid4()
    bp_evt_id = uuid4()
    await session.execute(
        text(
            'INSERT INTO bibliographic_production '
            '(id, title, type, researcher_id, sequence_code, year_, nature) '
            "VALUES (:id, 'Texto Divulgacao', 'TEXT_IN_NEWSPAPER_MAGAZINE', "
            ":rid, 1, 2024, 'REVISTA')"
        ),
        {'id': bp_mag_id, 'rid': r.id},
    )
    await session.execute(
        text(
            'INSERT INTO bibliographic_production '
            '(id, title, type, researcher_id, sequence_code, year_, nature) '
            "VALUES (:id, 'Artigo Evento X', 'WORK_IN_EVENT', :rid, 2, 2023, "
            "'COMPLETO')"
        ),
        {'id': bp_evt_id, 'rid': r.id},
    )
    await session.execute(
        text(
            'INSERT INTO bibliographic_production_work_in_event '
            '(bibliographic_production_id, event_name, event_classification) '
            "VALUES (:id, 'CBSoft 2023', 'INTERNACIONAL')"
        ),
        {'id': bp_evt_id},
    )
    await session.execute(
        text('REFRESH MATERIALIZED VIEW mv_canonical_magazine_texts;')
    )
    await session.execute(
        text('REFRESH MATERIALIZED VIEW mv_canonical_event_works;')
    )
    await session.commit()

    mag_list = client.get('/v2/production/magazine-text?q=Divulgacao')
    assert mag_list.status_code == HTTPStatus.OK, mag_list.text
    mag_data = mag_list.json()['data']
    assert len(mag_data) == 1
    assert mag_data[0]['title'] == 'Texto Divulgacao'

    mag_detail = client.get(
        f"/v2/production/magazine-text/{mag_data[0]['id']}"
    )
    assert mag_detail.status_code == HTTPStatus.OK
    assert mag_detail.json()['data']['nature'] == 'REVISTA'

    evt_list = client.get('/v2/production/event-work?q=CBSoft')
    assert evt_list.status_code == HTTPStatus.OK, evt_list.text
    evt_data = evt_list.json()['data']
    assert len(evt_data) == 1
    assert evt_data[0]['event_name'] == 'CBSoft 2023'

    evt_detail = client.get(f"/v2/production/event-work/{evt_data[0]['id']}")
    assert evt_detail.status_code == HTTPStatus.OK
    assert evt_detail.json()['data']['event_classification'] == 'INTERNACIONAL'

    metric = client.get('/v2/metrics/production/event-work')
    assert metric.status_code == HTTPStatus.OK
    assert metric.json()['data'] == [{'period': 2023, 'value': 1}]
