# ruff: noqa: E501, PLR2004
import uuid
from http import HTTPStatus

import pytest
from sqlalchemy import text

from simcc.core.db.models.expertise import (
    AreaExpertise,
    GreatAreaExpertise,
    SubAreaExpertise,
)
from simcc.core.db.models.production import (
    Foment,
)
from simcc.core.db.models.researcher import ResearcherAreaExpertise
from tests.factories.production import next_sequence_code


def _names(response):
    assert response.status_code == HTTPStatus.OK, response.text
    return {item['name'] for item in response.json()['data']}


def _titles(response):
    assert response.status_code == HTTPStatus.OK, response.text
    return {item['title'] for item in response.json()['data']}


def _facet(response, name):
    assert response.status_code == HTTPStatus.OK, response.text
    return {
        item['label']: (item['count'], item['selected'])
        for item in response.json()['facets'][name]['items']
    }


async def _link_great_area(session, researcher, great_area_name):
    gae = GreatAreaExpertise(name=great_area_name)
    session.add(gae)
    await session.flush()

    ae = AreaExpertise(
        name='Area ' + great_area_name, great_area_expertise_id=gae.id
    )
    session.add(ae)
    await session.flush()

    sub = SubAreaExpertise(
        name='SubArea ' + great_area_name, area_expertise_id=ae.id
    )
    session.add(sub)
    await session.flush()

    link = ResearcherAreaExpertise(
        researcher_id=researcher.id,
        sub_area_expertise_id=sub.id,
        great_area_expertise_id=gae.id,
        area_expertise_id=ae.id,
    )
    session.add(link)
    await session.commit()


async def _add_foment(session, researcher, modality_name):
    f = Foment(
        researcher_id=researcher.id,
        sequence_code=next_sequence_code(),
        modality_name=modality_name,
    )
    session.add(f)
    await session.commit()


@pytest.mark.asyncio
async def test_researcher_area_filter_and_facet(
    client, session, researcher_factory, refresh_mvs
):
    r1 = await researcher_factory(name='Pesquisador Exatas')
    r2 = await researcher_factory(name='Pesquisador Biologicas')
    await _link_great_area(session, r1, 'CIENCIAS_EXATAS_E_DA_TERRA')
    await _link_great_area(session, r2, 'CIENCIAS_BIOLOGICAS')
    await refresh_mvs()

    # 1. Filtro com underscore
    res1 = client.get(
        '/v2/researcher?area=CIENCIAS_EXATAS_E_DA_TERRA&facets=area'
    )
    assert _names(res1) == {'Pesquisador Exatas'}
    assert _facet(res1, 'area') == {
        'CIENCIAS_EXATAS_E_DA_TERRA': (1, True),
        'CIENCIAS_BIOLOGICAS': (1, False),
    }

    # 2. Filtro com espaço (normalização)
    res2 = client.get('/v2/researcher?area=CIENCIAS EXATAS E DA TERRA')
    assert _names(res2) == {'Pesquisador Exatas'}


@pytest.mark.asyncio
async def test_researcher_modality_filter_and_facet(
    client, session, researcher_factory, refresh_mvs
):
    r1 = await researcher_factory(name='Bolsista 1A')
    r2 = await researcher_factory(name='Bolsista 2')
    await _add_foment(session, r1, 'Produtividade em Pesquisa - 1A')
    await _add_foment(session, r2, 'Produtividade em Pesquisa - 2')
    await refresh_mvs()

    res = client.get(
        '/v2/researcher?modality=Produtividade em Pesquisa - 1A&facets=modality'
    )
    assert _names(res) == {'Bolsista 1A'}
    assert _facet(res, 'modality') == {
        'Produtividade em Pesquisa - 1A': (1, True),
        'Produtividade em Pesquisa - 2': (1, False),
    }


@pytest.mark.asyncio
async def test_article_magazine_and_issn_filters(
    client, session, researcher_factory, refresh_mvs
):
    author = await researcher_factory()

    # Artigo 1
    p1_id = uuid.uuid4()
    m1_id = uuid.uuid4()
    await session.execute(
        text("""
        INSERT INTO bibliographic_production
            (id, researcher_id, sequence_code, title, year_, type)
        VALUES (:id, :rid, 1, 'Estudo na Nature', 2024, 'ARTICLE')
        """),
        {'id': p1_id, 'rid': author.id},
    )
    await session.execute(
        text("""
        INSERT INTO periodical_magazine (id, name, issn)
        VALUES (:id, 'Nature Journal', '0028-0836')
        """),
        {'id': m1_id},
    )
    await session.execute(
        text("""
        INSERT INTO bibliographic_production_article (id, bibliographic_production_id, periodical_magazine_id, periodical_magazine_name, issn, qualis)
        VALUES (:id, :pid, :mid, 'Nature Journal', '0028-0836', 'A1')
        """),
        {'id': uuid.uuid4(), 'pid': p1_id, 'mid': m1_id},
    )

    # Artigo 2
    p2_id = uuid.uuid4()
    m2_id = uuid.uuid4()
    await session.execute(
        text("""
        INSERT INTO bibliographic_production
            (id, researcher_id, sequence_code, title, year_, type)
        VALUES (:id, :rid, 2, 'Estudo na Science', 2024, 'ARTICLE')
        """),
        {'id': p2_id, 'rid': author.id},
    )
    await session.execute(
        text("""
        INSERT INTO periodical_magazine (id, name, issn)
        VALUES (:id, 'Science Journal', '0036-8075')
        """),
        {'id': m2_id},
    )
    await session.execute(
        text("""
        INSERT INTO bibliographic_production_article (id, bibliographic_production_id, periodical_magazine_id, periodical_magazine_name, issn, qualis)
        VALUES (:id, :pid, :mid, 'Science Journal', '0036-8075', 'A1')
        """),
        {'id': uuid.uuid4(), 'pid': p2_id, 'mid': m2_id},
    )
    await session.commit()
    await refresh_mvs()

    # Filtro por magazine_name
    res_mag = client.get(
        '/v2/production/article?magazine_name=Nature Journal&facets=magazine_name'
    )
    assert _titles(res_mag) == {'Estudo na Nature'}
    assert _facet(res_mag, 'magazine_name') == {
        'Nature Journal': (1, True),
        'Science Journal': (1, False),
    }

    # Filtro por issn
    res_issn = client.get('/v2/production/article?issn=0036-8075&facets=issn')
    assert _titles(res_issn) == {'Estudo na Science'}
    assert _facet(res_issn, 'issn') == {
        '0036-8075': (1, True),
        '0028-0836': (1, False),
    }


@pytest.mark.asyncio
async def test_production_area_filter_and_facet(
    client, session, researcher_factory, refresh_mvs
):
    author1 = await researcher_factory(name='Autor Exatas')
    author2 = await researcher_factory(name='Autor Biologicas')
    await _link_great_area(session, author1, 'CIENCIAS_EXATAS_E_DA_TERRA')
    await _link_great_area(session, author2, 'CIENCIAS_BIOLOGICAS')

    p1_id = uuid.uuid4()
    p2_id = uuid.uuid4()
    await session.execute(
        text("""
        INSERT INTO bibliographic_production
            (id, researcher_id, sequence_code, title, year_, type)
        VALUES (:id, :rid, 1, 'Livro de Computacao', 2024, 'BOOK')
        """),
        {'id': p1_id, 'rid': author1.id},
    )
    await session.execute(
        text("""
        INSERT INTO bibliographic_production_book (id, bibliographic_production_id, isbn)
        VALUES (:id, :pid, '111-222')
        """),
        {'id': uuid.uuid4(), 'pid': p1_id},
    )

    await session.execute(
        text("""
        INSERT INTO bibliographic_production
            (id, researcher_id, sequence_code, title, year_, type)
        VALUES (:id, :rid, 1, 'Livro de Botanica', 2024, 'BOOK')
        """),
        {'id': p2_id, 'rid': author2.id},
    )
    await session.execute(
        text("""
        INSERT INTO bibliographic_production_book (id, bibliographic_production_id, isbn)
        VALUES (:id, :pid, '333-444')
        """),
        {'id': uuid.uuid4(), 'pid': p2_id},
    )
    await session.commit()
    await refresh_mvs()

    res = client.get(
        '/v2/production/book?area=CIENCIAS_EXATAS_E_DA_TERRA&facets=area'
    )
    assert _titles(res) == {'Livro de Computacao'}
    assert _facet(res, 'area') == {
        'CIENCIAS_EXATAS_E_DA_TERRA': (1, True),
        'CIENCIAS_BIOLOGICAS': (1, False),
    }
