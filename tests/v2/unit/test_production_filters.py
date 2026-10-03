# ruff: noqa: PLR2004
from http import HTTPStatus
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text


def _titles(response):
    assert response.status_code == HTTPStatus.OK, response.text
    return {item['title'] for item in response.json()['data']}


def _facet(response, name):
    assert response.status_code == HTTPStatus.OK, response.text
    return {
        item['label']: (item['count'], item['selected'])
        for item in response.json()['facets'][name]['items']
    }


@pytest_asyncio.fixture
def article_factory(session):
    async def create(researcher, title, year=2024, qualis='A1'):
        production_id = uuid4()
        await session.execute(
            text("""
            INSERT INTO bibliographic_production
                (id, researcher_id, title, year_, type, relevance, has_image)
            VALUES (:id, :researcher_id, :title, :year, 'ARTICLE', true, false)
            """),
            {
                'id': production_id,
                'researcher_id': researcher.id,
                'title': title,
                'year': year,
            },
        )
        magazine_id = uuid4()
        await session.execute(
            text("""
            INSERT INTO periodical_magazine (id, name, issn)
            VALUES (:id, 'Revista', '1234-5678')
            """),
            {'id': magazine_id},
        )
        await session.execute(
            text("""
            INSERT INTO bibliographic_production_article
                (id, bibliographic_production_id, periodical_magazine_id,
                 periodical_magazine_name, issn, qualis)
            VALUES (:id, :production_id, :magazine_id, 'Revista',
                    '1234-5678', :qualis)
            """),
            {
                'id': uuid4(),
                'production_id': production_id,
                'magazine_id': magazine_id,
                'qualis': qualis,
            },
        )
        await session.commit()

    return create


@pytest_asyncio.fixture
def event_factory(session):
    async def create(researcher, title, nature, form='Convidado', year=2024):
        await session.execute(
            text("""
            INSERT INTO participation_events
                (id, researcher_id, title, event_name, nature,
                 form_participation, type_participation, year)
            VALUES (:id, :researcher_id, :title, 'Evento', :nature, :form,
                    'Apresentação Oral', :year)
            """),
            {
                'id': uuid4(),
                'researcher_id': researcher.id,
                'title': title,
                'nature': nature,
                'form': form,
                'year': year,
            },
        )
        await session.commit()

    return create


@pytest_asyncio.fixture
def patent_factory(session):
    async def create(researcher, title, category, grant_date=None):
        await session.execute(
            text("""
            INSERT INTO patent
                (id, researcher_id, title, category, development_year,
                 code, grant_date)
            VALUES (:id, :researcher_id, :title, :category, '2024', :code,
                    :grant_date)
            """),
            {
                'id': uuid4(),
                'researcher_id': researcher.id,
                'title': title,
                'category': category,
                'code': f'BR {uuid4().hex[:12]}',
                'grant_date': grant_date,
            },
        )
        await session.commit()

    return create


# --- filtros territoriais (vínculos dos autores) --------------------------


@pytest.mark.asyncio
async def test_identity_territory_filter_and_facet(  # noqa: PLR0913, PLR0917
    client,
    researcher_factory,
    researcher_institution_factory,
    article_factory,
    refresh_mvs,
):
    sisal = await researcher_factory(name='Autora Sisal')
    reconcavo = await researcher_factory(name='Autor Reconcavo')
    await researcher_institution_factory(
        researcher_id=sisal.id, identity_territory='Sisal'
    )
    await researcher_institution_factory(
        researcher_id=reconcavo.id, identity_territory='Recôncavo'
    )
    await article_factory(sisal, 'Artigo do Sisal Um')
    await article_factory(sisal, 'Artigo do Sisal Dois')
    await article_factory(reconcavo, 'Artigo do Reconcavo')
    await refresh_mvs()

    response = client.get(
        '/v2/production/article?identity_territory=Sisal'
        '&facets=identity_territory'
    )

    assert _titles(response) == {'Artigo do Sisal Um', 'Artigo do Sisal Dois'}
    # Disjuntivo: o próprio filtro não esconde os outros territórios
    assert _facet(response, 'identity_territory') == {
        'Sisal': (2, True),
        'Recôncavo': (1, False),
    }


@pytest.mark.asyncio
async def test_city_filter_and_facet(  # noqa: PLR0913, PLR0917
    client,
    researcher_factory,
    researcher_institution_factory,
    city_factory,
    event_factory,
    refresh_mvs,
):
    salvador = await city_factory(name='Salvador')
    feira = await city_factory(name='Feira de Santana')
    a = await researcher_factory(name='Participante Salvador')
    b = await researcher_factory(name='Participante Feira')
    await researcher_institution_factory(
        researcher_id=a.id, city_id=salvador.id
    )
    await researcher_institution_factory(researcher_id=b.id, city_id=feira.id)
    await event_factory(a, 'Palestra em Salvador', 'Congresso')
    await event_factory(b, 'Palestra em Feira', 'Congresso')
    await refresh_mvs()

    response = client.get(
        f'/v2/production/event?city_id={salvador.id}&facets=city'
    )

    assert _titles(response) == {'Palestra em Salvador'}
    assert _facet(response, 'city') == {
        'Salvador': (1, True),
        'Feira de Santana': (1, False),
    }


# --- facets comuns --------------------------------------------------------


@pytest.mark.asyncio
async def test_year_and_qualis_facets_respect_other_filters(
    client, researcher_factory, article_factory, refresh_mvs
):
    author = await researcher_factory()
    await article_factory(author, 'Redes neurais A', year=2024, qualis='A1')
    await article_factory(author, 'Redes neurais B', year=2024, qualis='A2')
    await article_factory(author, 'Redes neurais C', year=2020, qualis='A1')
    await article_factory(author, 'Outro assunto', year=2024, qualis='A1')
    await refresh_mvs()

    response = client.get(
        '/v2/production/article?q=redes&qualis=A1&year_start=2024'
        '&facets=year,qualis'
    )

    assert _titles(response) == {'Redes neurais A'}
    # `year` ignora o intervalo de anos; `qualis` ignora o próprio filtro
    assert _facet(response, 'year') == {
        '2024': (1, False),
        '2020': (1, False),
    }
    assert _facet(response, 'qualis') == {
        'A1': (1, True),
        'A2': (1, False),
    }


@pytest.mark.asyncio
async def test_facet_counts_canonical_productions_once(
    client, researcher_factory, article_factory, refresh_mvs
):
    first = await researcher_factory()
    second = await researcher_factory()
    await article_factory(first, 'Artigo em coautoria')
    await article_factory(second, 'Artigo em coautoria')
    await refresh_mvs()

    response = client.get('/v2/production/article?facets=year')

    assert response.json()['pagination']['total_items'] == 1
    assert _facet(response, 'year') == {'2024': (1, False)}


# --- filtros próprios de cada tipo ----------------------------------------


@pytest.mark.asyncio
async def test_event_nature_filter_and_facet(
    client, researcher_factory, event_factory, refresh_mvs
):
    author = await researcher_factory()
    await event_factory(author, 'Trabalho no congresso', 'Congresso')
    await event_factory(author, 'Trabalho no seminario', 'Seminário')
    await event_factory(
        author, 'Ouvinte no seminario', 'Seminário', form='Ouvinte'
    )
    await refresh_mvs()

    response = client.get(
        '/v2/production/event?nature=Congresso&form_participation=Convidado'
        '&facets=nature,form_participation'
    )

    assert _titles(response) == {'Trabalho no congresso'}
    assert _facet(response, 'nature') == {
        'Congresso': (1, True),
        'Seminário': (1, False),
    }
    assert _facet(response, 'form_participation') == {
        'Convidado': (1, True),
    }


@pytest.mark.asyncio
async def test_patent_category_and_granted_filters(
    client, researcher_factory, patent_factory, refresh_mvs
):
    author = await researcher_factory()
    await patent_factory(author, 'Produto concedido', 'Produto', '2024-01-10')
    await patent_factory(author, 'Produto depositado', 'Produto')
    await patent_factory(author, 'Processo depositado', 'Processo')
    await refresh_mvs()

    granted = client.get('/v2/production/patent?granted=true')
    pending = client.get(
        '/v2/production/patent?granted=false&category=Produto&facets=category'
    )

    assert _titles(granted) == {'Produto concedido'}
    assert _titles(pending) == {'Produto depositado'}
    assert _facet(pending, 'category') == {
        'Produto': (1, True),
        'Processo': (1, False),
    }


# --- contrato -------------------------------------------------------------


@pytest.mark.asyncio
async def test_facets_are_opt_in(client):
    response = client.get('/v2/production/book')

    assert response.json()['facets'] is None


@pytest.mark.parametrize(
    'url',
    [
        '/v2/production/article?unknown=1',
        '/v2/production/event?qualis=A1',
        '/v2/production/book?facets=qualis',
        '/v2/production/article?facets=nature',
        '/v2/production/patent?facets=unknown',
        '/v2/production/software?facet_limit=0',
        '/v2/production/article?city_id=not-a-uuid',
    ],
)
def test_invalid_params_return_422(client, url):
    response = client.get(url)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_second_request_is_served_from_cache(
    client, researcher_factory, article_factory, refresh_mvs
):
    author = await researcher_factory()
    await article_factory(author, 'Artigo em cache')
    await refresh_mvs()
    url = '/v2/production/article?q=cache&facets=year'

    first = client.get(url).json()
    second = client.get(url).json()

    assert first['meta']['cached'] is False
    assert second['meta']['cached'] is True
    for field in ('data', 'pagination', 'facets', 'sort', 'filters_applied'):
        assert second[field] == first[field]


@pytest.mark.asyncio
async def test_cache_is_separate_per_production_type(client):
    client.get('/v2/production/book')

    response = client.get('/v2/production/software')

    assert response.json()['meta']['cached'] is False
