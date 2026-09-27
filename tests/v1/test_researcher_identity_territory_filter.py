from http import HTTPStatus

import pytest


def _researcher_names(response):
    assert response.status_code == HTTPStatus.OK, response.text
    return {r['name'] for r in response.json()}


@pytest.mark.asyncio
async def test_filter_researcher_by_identity_territory(
    client, researcher_factory, researcher_institution_factory
):
    sisal_researcher = await researcher_factory(name='Pesquisador Sisal')
    reconcavo_researcher = await researcher_factory(
        name='Pesquisador Reconcavo'
    )
    await researcher_factory(name='Pesquisador Sem Territorio')

    await researcher_institution_factory(
        researcher_id=sisal_researcher.id,
        identity_territory='Sisal',
    )
    await researcher_institution_factory(
        researcher_id=reconcavo_researcher.id,
        identity_territory='Recôncavo',
    )

    # Test /researcher
    res_single = client.get('/researcher?identity_territory=Sisal')
    assert _researcher_names(res_single) == {'Pesquisador Sisal'}

    # Test /researchers
    res_plural = client.get('/researchers?identity_territory=Sisal')
    assert _researcher_names(res_plural) == {'Pesquisador Sisal'}


@pytest.mark.asyncio
async def test_filter_researcher_multiple_territories_semicolon(
    client, researcher_factory, researcher_institution_factory
):
    sisal_researcher = await researcher_factory(name='Pesquisador Sisal')
    reconcavo_researcher = await researcher_factory(
        name='Pesquisador Reconcavo'
    )
    portal_researcher = await researcher_factory(name='Pesquisador Portal')

    await researcher_institution_factory(
        researcher_id=sisal_researcher.id,
        identity_territory='Sisal',
    )
    await researcher_institution_factory(
        researcher_id=reconcavo_researcher.id,
        identity_territory='Recôncavo',
    )
    await researcher_institution_factory(
        researcher_id=portal_researcher.id,
        identity_territory='Portal do Sertão',
    )

    response = client.get('/researchers?identity_territory=Sisal;Recôncavo')
    assert _researcher_names(response) == {
        'Pesquisador Sisal',
        'Pesquisador Reconcavo',
    }


@pytest.mark.asyncio
async def test_filter_researcher_case_insensitive(
    client, researcher_factory, researcher_institution_factory
):
    sisal_researcher = await researcher_factory(name='Pesquisador Sisal')
    await researcher_institution_factory(
        researcher_id=sisal_researcher.id,
        identity_territory='Sisal',
    )

    # Lowercase
    res_lower = client.get('/researchers?identity_territory=sisal')
    assert _researcher_names(res_lower) == {'Pesquisador Sisal'}

    # Uppercase
    res_upper = client.get('/researchers?identity_territory=SISAL')
    assert _researcher_names(res_upper) == {'Pesquisador Sisal'}


@pytest.mark.asyncio
async def test_filter_researcher_inexistent_territory(
    client, researcher_factory, researcher_institution_factory
):
    researcher = await researcher_factory(name='Pesquisador Sisal')
    await researcher_institution_factory(
        researcher_id=researcher.id,
        identity_territory='Sisal',
    )

    response = client.get('/researchers?identity_territory=Inexistente')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


@pytest.mark.asyncio
async def test_researcher_filter_endpoint_returns_territories(
    client, researcher_factory, researcher_institution_factory
):
    sisal = await researcher_factory(name='Pesquisador Sisal')
    reconcavo = await researcher_factory(name='Pesquisador Reconcavo')

    await researcher_institution_factory(
        researcher_id=sisal.id,
        identity_territory='Sisal',
    )
    await researcher_institution_factory(
        researcher_id=reconcavo.id,
        identity_territory='Recôncavo',
    )

    response = client.get('/researcher_filter')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert 'identity_territory' in data
    assert 'Sisal' in data['identity_territory']
    assert 'Recôncavo' in data['identity_territory']
