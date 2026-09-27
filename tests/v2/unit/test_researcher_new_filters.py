# ruff: noqa: PLR2004
from http import HTTPStatus

import pytest


def _names(response):
    assert response.status_code == HTTPStatus.OK, response.text
    return {item['name'] for item in response.json()['data']}


def _facet(response, name):
    assert response.status_code == HTTPStatus.OK, response.text
    return {
        item['label']: (item['count'], item['selected'])
        for item in response.json()['facets'][name]['items']
    }


# --- território de identidade --------------------------------------------


@pytest.mark.asyncio
async def test_identity_territory_filter_and_facet(
    client, researcher_factory, researcher_institution_factory, refresh_mvs
):
    sisal = await researcher_factory(name='Pesquisador Sisal')
    reconcavo = await researcher_factory(name='Pesquisador Reconcavo')
    await researcher_factory(name='Sem Territorio')
    await researcher_institution_factory(
        researcher_id=sisal.id, identity_territory='Sisal'
    )
    await researcher_institution_factory(
        researcher_id=reconcavo.id, identity_territory='Recôncavo'
    )
    await refresh_mvs()

    response = client.get(
        '/v2/researcher?identity_territory=Sisal&facets=identity_territory'
    )

    assert _names(response) == {'Pesquisador Sisal'}
    # Disjuntivo: o próprio filtro não esconde os outros territórios
    assert _facet(response, 'identity_territory') == {
        'Recôncavo': (1, False),
        'Sisal': (1, True),
    }


@pytest.mark.asyncio
async def test_identity_territory_selected_without_results_is_kept(
    client, researcher_factory
):
    await researcher_factory()

    response = client.get(
        '/v2/researcher?identity_territory=Inexistente'
        '&facets=identity_territory'
    )

    assert response.json()['data'] == []
    facet = response.json()['facets']['identity_territory']
    assert facet == {
        'total': 0,
        'items': [
            {
                'value': 'Inexistente',
                'label': 'Inexistente',
                'count': 0,
                'acronym': None,
                'selected': True,
            }
        ],
    }


# --- cidade ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_city_filter_and_facet(
    client,
    researcher_factory,
    researcher_institution_factory,
    city_factory,
    refresh_mvs,
):
    salvador = await city_factory(name='Salvador')
    feira = await city_factory(name='Feira de Santana')
    a = await researcher_factory(name='Em Salvador')
    b = await researcher_factory(name='Em Feira')
    await researcher_institution_factory(
        researcher_id=a.id, city_id=salvador.id
    )
    await researcher_institution_factory(researcher_id=b.id, city_id=feira.id)
    await refresh_mvs()

    response = client.get(f'/v2/researcher?city_id={salvador.id}&facets=city')

    assert _names(response) == {'Em Salvador'}
    assert _facet(response, 'city') == {
        'Feira de Santana': (1, False),
        'Salvador': (1, True),
    }


# --- classificação e titulação -------------------------------------------


@pytest.mark.asyncio
async def test_classification_filter_and_facet(client, researcher_factory):
    await researcher_factory(name='Classe A', classification='A+')
    await researcher_factory(name='Classe E', classification='E')

    response = client.get(
        '/v2/researcher?classification=A%2B&facets=classification'
    )

    assert _names(response) == {'Classe A'}
    assert _facet(response, 'classification') == {
        'A+': (1, True),
        'E': (1, False),
    }


@pytest.mark.asyncio
async def test_classification_invalid_value_is_rejected(client):
    response = client.get('/v2/researcher?classification=Z')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_graduation_filter_accepts_multiple_values(
    client, researcher_factory
):
    await researcher_factory(name='Doutora', graduation='Doutorado')
    await researcher_factory(name='Mestre', graduation='Mestrado')
    await researcher_factory(name='Graduada', graduation='Graduação')

    response = client.get(
        '/v2/researcher?graduation=Doutorado&graduation=Mestrado'
        '&facets=graduation'
    )

    assert _names(response) == {'Doutora', 'Mestre'}
    assert _facet(response, 'graduation') == {
        'Doutorado': (1, True),
        'Graduação': (1, False),
        'Mestrado': (1, True),
    }


# --- tipo de produção -----------------------------------------------------


@pytest.mark.asyncio
async def test_source_type_without_q_requires_production_of_type(
    client, researcher_factory, production_factory
):
    author = await researcher_factory(name='Tem Livro')
    await researcher_factory(name='Sem Livro')
    await production_factory(author, 'Um livro', type_='BOOK')

    response = client.get('/v2/researcher?source_type=BOOK&facets=source_type')

    assert _names(response) == {'Tem Livro'}
    assert _facet(response, 'source_type') == {'BOOK': (1, True)}


@pytest.mark.asyncio
async def test_source_type_with_q_ignores_profile_and_other_types(
    client, researcher_factory, production_factory
):
    # Casa só pelo nome (perfil): não conta quando o tipo é restrito
    await researcher_factory(name='Dengue da Silva')
    article_author = await researcher_factory(name='Autora Artigo')
    software_author = await researcher_factory(name='Autor Software')
    await production_factory(article_author, 'Vigilancia da dengue')
    await production_factory(
        software_author, 'Painel de dengue', type_='SOFTWARE'
    )

    response = client.get(
        '/v2/researcher?q=dengue&source_type=ARTICLE'
        '&facets=source_type&include=matches'
    )

    assert _names(response) == {'Autora Artigo'}
    # O facet de tipo é disjuntivo: mostra SOFTWARE para ampliar a busca
    assert _facet(response, 'source_type') == {
        'ARTICLE': (1, True),
        'SOFTWARE': (1, False),
    }
    matches = response.json()['data'][0]['matches']
    assert matches['by_type'] == {'ARTICLE': 1}
    assert {item['source_type'] for item in matches['items']} == {'ARTICLE'}


@pytest.mark.asyncio
async def test_source_type_invalid_value_is_rejected(client):
    response = client.get('/v2/researcher?source_type=POEM')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


# --- correções de consistência --------------------------------------------


@pytest.mark.asyncio
async def test_matches_respect_year_range(
    client, researcher_factory, production_factory
):
    author = await researcher_factory(name='Autora Anos')
    await production_factory(author, 'Dengue em 2010', year=2010)
    await production_factory(author, 'Dengue em 2022', year=2022)

    response = client.get(
        '/v2/researcher?q=dengue&year_start=2020&include=matches'
    )

    matches = response.json()['data'][0]['matches']
    assert matches['total'] == 1
    assert [item['year'] for item in matches['items']] == [2022]


@pytest.mark.asyncio
async def test_year_facet_is_disjunctive_with_q(
    client, researcher_factory, production_factory
):
    author = await researcher_factory(name='Autora Historico')
    await production_factory(author, 'Dengue antiga', year=2010)
    await production_factory(author, 'Dengue recente', year=2022)

    response = client.get(
        '/v2/researcher?q=dengue&year_start=2020&facets=year'
    )

    # O filtro de anos não esconde os anos de fora do intervalo no facet
    assert set(_facet(response, 'year')) == {'2010', '2022'}


@pytest.mark.asyncio
async def test_year_facet_with_q_counts_only_matching_works(
    client, researcher_factory, production_factory
):
    author = await researcher_factory(name='Autora Temas')
    await production_factory(author, 'Dengue urbana', year=2021)
    await production_factory(author, 'Redes neurais', year=2015)

    response = client.get('/v2/researcher?q=dengue&facets=year')

    assert set(_facet(response, 'year')) == {'2021'}
