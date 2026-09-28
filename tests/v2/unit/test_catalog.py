# ruff: noqa: PLR2004
from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_list_institutions_pagination(client, institution_factory):
    inst1 = await institution_factory(
        name='Universidade Federal da Bahia', acronym='UFBA'
    )
    inst2 = await institution_factory(
        name='Universidade Estadual de Feira de Santana', acronym='UEFS'
    )

    response = client.get('/v2/institution?page=1&per_page=10')
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert 'data' in body
    assert 'pagination' in body
    assert body['pagination']['total_items'] >= 2

    ids = [item['id'] for item in body['data']]
    assert str(inst1.id) in ids
    assert str(inst2.id) in ids


@pytest.mark.asyncio
async def test_search_institutions_by_query(client, institution_factory):
    await institution_factory(
        name='Instituto Tecnológico de Aeronáutica', acronym='ITA'
    )
    await institution_factory(
        name='Universidade Estadual de Campinas', acronym='UNICAMP'
    )

    # Busca por sigla
    res_acronym = client.get('/v2/institution?q=ITA')
    assert res_acronym.status_code == HTTPStatus.OK
    body = res_acronym.json()
    assert len(body['data']) == 1
    assert body['data'][0]['acronym'] == 'ITA'

    # Busca por nome
    res_name = client.get('/v2/institution?q=Campinas')
    assert res_name.status_code == HTTPStatus.OK
    body_name = res_name.json()
    assert len(body_name['data']) == 1
    assert body_name['data'][0]['acronym'] == 'UNICAMP'


@pytest.mark.asyncio
async def test_list_graduate_programs_pagination(
    client, graduate_program_factory
):
    gp1 = await graduate_program_factory(
        name='Programa de Pós-Graduação em Ciência da Computação',
        acronym='PGCOMP',
    )
    gp2 = await graduate_program_factory(
        name='Programa de Pós-Graduação em Mecatrônica',
        acronym='PPMEC',
    )

    response = client.get('/v2/graduate_program?page=1&per_page=10')
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert 'data' in body
    assert 'pagination' in body
    assert body['pagination']['total_items'] >= 2

    ids = [item['id'] for item in body['data']]
    assert str(gp1.graduate_program_id) in ids
    assert str(gp2.graduate_program_id) in ids


@pytest.mark.asyncio
async def test_search_graduate_programs_by_query(
    client, graduate_program_factory
):
    await graduate_program_factory(
        name='Mestrado em Engenharia Elétrica', acronym='MEEL'
    )
    await graduate_program_factory(
        name='Doutorado em Biotecnologia', acronym='DBIOT'
    )

    res_acronym = client.get('/v2/graduate_program?q=MEEL')
    assert res_acronym.status_code == HTTPStatus.OK
    body = res_acronym.json()
    assert len(body['data']) == 1
    assert body['data'][0]['acronym'] == 'MEEL'

    res_name = client.get('/v2/graduate_program?q=Biotecnologia')
    assert res_name.status_code == HTTPStatus.OK
    body_name = res_name.json()
    assert len(body_name['data']) == 1
    assert body_name['data'][0]['acronym'] == 'DBIOT'


@pytest.mark.asyncio
async def test_list_institutions_returns_institution_ref(
    client, institution_factory, institution_storage
):
    institution_storage('CIMG')
    with_images = await institution_factory(
        name='Catalogo Com Imagem', acronym='CIMG'
    )
    await institution_factory(
        name='Catalogo Sem Imagem',
        acronym='ISI',
        image='https://example.com/isi.png',
    )

    body = client.get('/v2/institution?q=Catalogo').json()
    items = {item['acronym']: item for item in body['data']}

    assert items['CIMG'] == {
        'id': str(with_images.id),
        'name': 'Catalogo Com Imagem',
        'acronym': 'CIMG',
        'image': '/storage/institutions/picture/CIMG.png',
        'cover': '/storage/institutions/covers/CIMG.jpg',
    }
    # Sem arquivo em disco, o logo cai para a coluna `institution.image`
    assert items['ISI']['image'] == 'https://example.com/isi.png'
    assert items['ISI']['cover'] is None
