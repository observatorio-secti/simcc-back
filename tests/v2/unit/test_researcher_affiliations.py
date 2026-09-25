# ruff: noqa: PLR2004
from http import HTTPStatus

import pytest

from simcc.v2.services.mv_refresh_service import (
    refresh_search_materialized_views,
)
from tests.factories.researcher import ResearcherFactory


@pytest.mark.asyncio
async def test_researcher_affiliations_full_link(
    client,
    researcher_factory,
    institution_factory,
    researcher_institution_factory,
    city_factory,
):
    researcher = await researcher_factory(name='Vinculo Completo')
    institution = await institution_factory(
        name='Instituto Afiliacao A', acronym='AFFA'
    )
    city = await city_factory(name='Salvador')
    await researcher_institution_factory(
        researcher_id=researcher.id,
        institution_id=institution.id,
        workload=40,
        identity_territory='Metropolitano de Salvador',
        city_id=city.id,
    )

    response = client.get('/v2/researcher?q=Completo')

    assert response.status_code == HTTPStatus.OK
    affiliations = response.json()['data'][0]['affiliations']
    catalog = client.get('/v2/institution?q=AFFA').json()['data']
    assert affiliations == [
        {
            'institution': catalog[0],
            'workload': 40.0,
            'identity_territory': 'Metropolitano de Salvador',
            'city': {'id': str(city.id), 'name': 'Salvador'},
        }
    ]


@pytest.mark.asyncio
async def test_researcher_affiliations_multiple_institutions(
    client,
    researcher_factory,
    institution_factory,
    researcher_institution_factory,
):
    researcher = await researcher_factory(name='Vinculo Multiplo')
    inst_b = await institution_factory(name='Instituto Multiplo B')
    inst_a = await institution_factory(name='Instituto Multiplo A')
    await researcher_institution_factory(
        researcher_id=researcher.id, institution_id=inst_b.id
    )
    await researcher_institution_factory(
        researcher_id=researcher.id, institution_id=inst_a.id
    )

    response = client.get('/v2/researcher?q=Multiplo')

    affiliations = response.json()['data'][0]['affiliations']
    assert [a['institution']['name'] for a in affiliations] == [
        'Instituto Multiplo A',
        'Instituto Multiplo B',
    ]
    assert affiliations[0]['workload'] is None
    assert affiliations[0]['identity_territory'] is None
    assert affiliations[0]['city'] is None


@pytest.mark.asyncio
async def test_researcher_affiliations_ignores_legacy_institution_id(
    client, session, institution_factory
):
    institution = await institution_factory()
    session.add(
        ResearcherFactory(name='Vinculo Legado', institution_id=institution.id)
    )
    await session.commit()
    await refresh_search_materialized_views(session)

    response = client.get('/v2/researcher?q=Legado')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['data'][0]['affiliations'] == []

    # A coluna legada também não alimenta o filtro por instituição
    response = client.get(f'/v2/researcher?institution_id={institution.id}')
    assert response.json()['data'] == []


@pytest.mark.asyncio
async def test_researcher_affiliations_are_scoped_per_researcher(
    client,
    researcher_factory,
    institution_factory,
    researcher_institution_factory,
):
    alice = await researcher_factory(name='Alice Escopo')
    bob = await researcher_factory(name='Bob Escopo')
    inst = await institution_factory(name='Instituto Escopo')
    await researcher_institution_factory(
        researcher_id=alice.id, institution_id=inst.id
    )

    response = client.get('/v2/researcher?q=Escopo')

    data = {r['researcher_id']: r for r in response.json()['data']}
    assert len(data[str(alice.id)]['affiliations']) == 1
    assert data[str(bob.id)]['affiliations'] == []
