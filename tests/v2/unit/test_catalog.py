# ruff: noqa: PLR2004
from http import HTTPStatus

import pytest

from simcc.core import utils
from simcc.core.db.models.miscellaneous import Labs
from simcc.core.db.models.production import Foment
from simcc.core.db.models.research_group import ResearchGroup
from simcc.core.settings import Settings, get_settings


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

    response = client.get('/v2/graduate-program?page=1&per_page=10')
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

    res_acronym = client.get('/v2/graduate-program?q=MEEL')
    assert res_acronym.status_code == HTTPStatus.OK
    body = res_acronym.json()
    assert len(body['data']) == 1
    assert body['data'][0]['acronym'] == 'MEEL'

    res_name = client.get('/v2/graduate-program?q=Biotecnologia')
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

    base_url = get_settings().storage_base_url
    assert items['CIMG'] == {
        'id': str(with_images.id),
        'name': 'Catalogo Com Imagem',
        'acronym': 'CIMG',
        'image': f'{base_url}/storage/institutions/picture/CIMG.png',
        'cover': f'{base_url}/storage/institutions/covers/CIMG.jpg',
    }
    # Sem arquivo em disco, o logo cai para a coluna `institution.image`
    assert items['ISI']['image'] == 'https://example.com/isi.png'
    assert items['ISI']['cover'] is None


@pytest.mark.asyncio
async def test_list_institutions_excludes_without_acronym(
    client, institution_factory
):
    with_acronym = await institution_factory(
        name='Filtro Acronimo Com Sigla', acronym='FACS'
    )
    await institution_factory(name='Filtro Acronimo Sem Sigla', acronym=None)
    await institution_factory(name='Filtro Acronimo Vazio', acronym='   ')

    response = client.get(
        '/v2/institution?q=Filtro%20Acronimo&page=1&per_page=20'
        '&sort_by=name&sort_order=asc'
    )
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['pagination']['total_items'] == 1
    assert [item['id'] for item in body['data']] == [str(with_acronym.id)]


@pytest.mark.asyncio
async def test_institution_urls_use_configured_public_base(
    client, institution_factory, institution_storage, monkeypatch
):
    institution_storage('UFRB')
    inst = await institution_factory(name='UFRB', acronym='UFRB')

    # Fallback para URL quando STORAGE_URL não está definida
    dev_settings = Settings(
        DATABASE_URL='postgresql+psycopg://u:p@localhost/db',
        URL='http://localhost:8088/',
        STORAGE_URL=None,
    )
    monkeypatch.setattr(utils, 'get_settings', lambda: dev_settings)
    utils.get_institution_logo_url.cache_clear()
    utils.get_institution_cover_url.cache_clear()

    detail_dev = client.get(f'/v2/institution/{inst.id}').json()['data']
    assert detail_dev['image'] == (
        'http://localhost:8088/storage/institutions/picture/UFRB.png'
    )
    assert detail_dev['cover'] == (
        'http://localhost:8088/storage/institutions/covers/UFRB.jpg'
    )

    # Sobrescrita via STORAGE_URL (CDN/S3 em produção)
    prod_settings = Settings(
        DATABASE_URL='postgresql+psycopg://u:p@localhost/db',
        URL='https://api.observatorio.example/',
        STORAGE_URL='https://cdn.observatorio.example/',
    )
    monkeypatch.setattr(utils, 'get_settings', lambda: prod_settings)
    utils.get_institution_logo_url.cache_clear()
    utils.get_institution_cover_url.cache_clear()

    list_prod = client.get('/v2/institution?q=UFRB').json()['data']
    assert list_prod[0]['image'] == (
        'https://cdn.observatorio.example/storage/institutions/picture/UFRB.png'
    )
    assert list_prod[0]['cover'] == (
        'https://cdn.observatorio.example/storage/institutions/covers/UFRB.jpg'
    )


@pytest.mark.asyncio
async def test_graduate_program_facets_including_city(
    client, graduate_program_factory
):
    await graduate_program_factory(
        name='Programa A',
        acronym='PPA',
        area='Ciência da Computação',
        modality='Acadêmico',
        rating='5',
        state='BA',
        city='Salvador',
    )
    await graduate_program_factory(
        name='Programa B',
        acronym='PPB',
        area='Engenharia Elétrica',
        modality='Profissional',
        rating='4',
        state='BA',
        city='Feira de Santana',
    )

    response = client.get(
        '/v2/graduate-program'
        '?page=1&per_page=20&sort_by=name&sort_order=asc'
        '&facets=institution&facets=area&facets=modality'
        '&facets=rating&facets=state&facets=city'
    )
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    facets = body['facets']
    assert set(facets) == {
        'institution',
        'area',
        'modality',
        'rating',
        'state',
        'city',
    }
    assert facets['institution']['param'] == 'institution_id'
    assert facets['city']['param'] == 'city'
    city_values = {item['value'] for item in facets['city']['items']}
    assert {'Salvador', 'Feira de Santana'} <= city_values

    # Faceta disjuntiva: filtrar por city ainda retorna todas as cidades
    filtered = client.get('/v2/graduate-program?city=Salvador&facets=city')
    assert filtered.status_code == HTTPStatus.OK
    filtered_body = filtered.json()
    assert len(filtered_body['data']) == 1
    assert filtered_body['data'][0]['city'] == 'Salvador'
    filtered_cities = {
        item['value'] for item in filtered_body['facets']['city']['items']
    }
    assert {'Salvador', 'Feira de Santana'} <= filtered_cities


@pytest.mark.asyncio
async def test_institution_detail_scholarships_groups_and_labs(
    client,
    session,
    institution_factory,
    researcher_factory,
    researcher_institution_factory,
):
    inst = await institution_factory(
        name='Universidade Completa', acronym='UCOM'
    )
    other_inst = await institution_factory(
        name='Outra Universidade', acronym='OUTR'
    )

    r1 = await researcher_factory(name='Pesquisadora PQ1A')
    r2 = await researcher_factory(name='Pesquisador PQ2')
    r3 = await researcher_factory(name='Pesquisador Sem Bolsa')
    r_other = await researcher_factory(name='Pesquisador Externo')

    await researcher_institution_factory(
        researcher_id=r1.id, institution_id=inst.id
    )
    await researcher_institution_factory(
        researcher_id=r2.id, institution_id=inst.id
    )
    await researcher_institution_factory(
        researcher_id=r3.id, institution_id=inst.id
    )
    await researcher_institution_factory(
        researcher_id=r_other.id, institution_id=other_inst.id
    )

    session.add_all([
        # r1 tem duas bolsas em modalidades diferentes -> 1 bolsista único
        Foment(
            researcher_id=r1.id,
            sequence_code=1,
            modality_name='Produtividade em Pesquisa',
            category_level_code='1A',
        ),
        Foment(
            researcher_id=r1.id,
            sequence_code=2,
            modality_name='Desenvolvimento Tecnológico',
            category_level_code='2',
        ),
        Foment(
            researcher_id=r2.id,
            sequence_code=1,
            modality_name='Produtividade em Pesquisa',
            category_level_code='2',
        ),
        # Bolsa de outra instituição não deve entrar
        Foment(
            researcher_id=r_other.id,
            sequence_code=1,
            modality_name='Produtividade em Pesquisa',
            category_level_code='1A',
        ),
        # Grupos: 1º líder, 2º líder, ambos na inst (dedup), e outro fora
        ResearchGroup(
            name='Grupo A',
            institution='UCOM',
            first_leader_id=r1.id,
        ),
        ResearchGroup(
            name='Grupo B',
            institution='UCOM',
            first_leader_id=r_other.id,
            second_leader_id=r2.id,
        ),
        ResearchGroup(
            name='Grupo C',
            institution='UCOM',
            first_leader_id=r1.id,
            second_leader_id=r3.id,
        ),
        ResearchGroup(
            name='Grupo Externo',
            institution='OUTR',
            first_leader_id=r_other.id,
        ),
        # Laboratórios
        Labs(
            hashed_id='lab-1',
            type='Pesquisa',
            name='Lab 1',
            researcher_id=r1.id,
            institution_id=inst.id,
        ),
        Labs(
            hashed_id='lab-2',
            type='Ensino',
            name='Lab 2',
            researcher_id=r2.id,
            institution_id=inst.id,
        ),
        Labs(
            hashed_id='lab-other',
            type='Pesquisa',
            name='Lab Externo',
            researcher_id=r_other.id,
            institution_id=other_inst.id,
        ),
    ])
    await session.commit()

    response = client.get(f'/v2/institution/{inst.id}')
    assert response.status_code == HTTPStatus.OK
    data = response.json()['data']

    assert data['counts'] == {
        'researchers': 3,
        'graduate_programs': 0,
        'scholarship_holders': 2,
        'research_groups': 3,
        'labs': 2,
    }
    assert data['scholarships'] == [
        {
            'modality': 'Desenvolvimento Tecnológico',
            'category_level': '2',
            'researchers': 1,
        },
        {
            'modality': 'Produtividade em Pesquisa',
            'category_level': '1A',
            'researchers': 1,
        },
        {
            'modality': 'Produtividade em Pesquisa',
            'category_level': '2',
            'researchers': 1,
        },
    ]
