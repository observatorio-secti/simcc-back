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


@pytest.mark.asyncio
async def test_researcher_filter_dynamic_scoping_by_terms_and_type(
    client, researcher_factory, researcher_institution_factory, article_factory
):
    sisal = await researcher_factory(
        name='Pesquisador Educacao', graduation='Doutorado'
    )
    reconcavo = await researcher_factory(
        name='Pesquisador Fisica', graduation='Mestrado'
    )

    await researcher_institution_factory(
        researcher_id=sisal.id,
        identity_territory='Sisal',
    )
    await researcher_institution_factory(
        researcher_id=reconcavo.id,
        identity_territory='Recôncavo',
    )

    await article_factory(sisal, 'Educacao inclusiva e inovacao')
    await article_factory(reconcavo, 'Fisica nuclear aplicada')

    # 1. Filtro global sem parâmetros retorna ambos
    res_global = client.get('/researcher_filter')
    assert res_global.status_code == HTTPStatus.OK
    data_global = res_global.json()
    assert set(data_global['identity_territory']) >= {'Sisal', 'Recôncavo'}
    assert set(data_global['graduation']) >= {'Doutorado', 'Mestrado'}

    # 2. Filtrando por terms=Educacao&type=ARTICLE
    res_edu = client.get('/researcher_filter?terms=Educacao&type=ARTICLE')
    assert res_edu.status_code == HTTPStatus.OK
    data_edu = res_edu.json()
    assert data_edu['identity_territory'] == ['Sisal']
    assert data_edu['graduation'] == ['Doutorado']

    # 3. Filtrando por terms=Fisica&type=ARTICLE
    res_fis = client.get('/researcher_filter?terms=Fisica&type=ARTICLE')
    assert res_fis.status_code == HTTPStatus.OK
    data_fis = res_fis.json()
    assert data_fis['identity_territory'] == ['Recôncavo']
    assert data_fis['graduation'] == ['Mestrado']

    # 4. Filtrando por termo inexistente
    res_none = client.get('/researcher_filter?terms=Inexistente&type=ARTICLE')
    assert res_none.status_code == HTTPStatus.OK
    data_none = res_none.json()
    assert data_none['identity_territory'] == []
    assert data_none['graduation'] == []
