# ruff: noqa: PLR2004, PLR0914
from http import HTTPStatus
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_validation_invalid_sort_by(client):
    response = client.get('/v2/production/article?by=invalid_column')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_validation_invalid_sort_order(client):
    response = client.get('/v2/production/article?order=sideways')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_validation_year_start_greater_than_year_end(client):
    url = '/v2/production/article?year_start=2025&year_end=2020'
    response = client.get(url)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_validation_invalid_year_bounds(client):
    response = client.get('/v2/production/article?year_start=1850')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_article_detail_not_found(client):
    fake_id = uuid4()
    response = client.get(f'/v2/production/article/{fake_id}')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_article_list_structure(client):
    response = client.get('/v2/production/article?page=1&per_page=5')
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert 'data' in body
    assert 'pagination' in body
    assert 'filters_applied' in body
    assert 'sort' in body
    assert 'meta' in body
    assert body['pagination']['page'] == 1
    assert body['pagination']['per_page'] == 5


@pytest.mark.asyncio
async def test_article_deduplication_and_detail(
    client, session, researcher_factory
):
    # Cria dois pesquisadores
    r1 = await researcher_factory(name='Pesquisador Um')
    r2 = await researcher_factory(name='Pesquisador Dois')

    bp_id1 = uuid4()
    bp_id2 = uuid4()
    doi = '10.1234/test-article-doi'
    title = 'Artigo Colaborativo Sobre Redes Complexas'
    year = 2024

    # Insere na tabela bibliographic_production (mesmo artigo 2x)
    await session.execute(
        text("""
        INSERT INTO bibliographic_production
            (id, researcher_id, sequence_code, title, year_, doi, type,
             relevance, has_image)
        VALUES
            (:id1, :r1, 1, :title, :year, :doi, 'ARTICLE', true, false),
            (:id2, :r2, 1, :title, :year, :doi, 'ARTICLE', true, false);
        """),
        {
            'id1': bp_id1,
            'id2': bp_id2,
            'r1': r1.id,
            'r2': r2.id,
            'title': title,
            'year': year,
            'doi': doi,
        },
    )

    # Insere revista periódica
    mag_id = uuid4()
    await session.execute(
        text("""
        INSERT INTO periodical_magazine (id, name, issn)
        VALUES (:id, 'Revista de Computacao', '1234-5678');
        """),
        {'id': mag_id},
    )

    # Insere metadados de artigo e revista
    await session.execute(
        text("""
        INSERT INTO bibliographic_production_article
            (id, bibliographic_production_id, periodical_magazine_id,
             periodical_magazine_name, issn, qualis)
        VALUES
            (:id1, :bp_id1, :mag_id, 'Revista', '1234-5678', 'A1'),
            (:id2, :bp_id2, :mag_id, 'Revista', '1234-5678', 'A1');
        """),
        {
            'id1': uuid4(),
            'id2': uuid4(),
            'bp_id1': bp_id1,
            'bp_id2': bp_id2,
            'mag_id': mag_id,
        },
    )

    # Insere resumo OpenAlex associado a apenas uma das produções
    await session.execute(
        text("""
        INSERT INTO openalex_article
            (id, article_id, abstract, citations_count, pdf, keywords)
        VALUES
            (:id, :bp_id1, :abstract, 42, 'https://example.com/pdf', 'redes');
        """),
        {
            'id': uuid4(),
            'bp_id1': bp_id1,
            'abstract': 'Comportamento de redes complexas em sistemas.',
        },
    )

    await session.commit()

    # Atualiza a MV para capturar os dados inseridos
    await session.execute(
        text('REFRESH MATERIALIZED VIEW mv_canonical_articles;')
    )
    await session.commit()

    # 1. Busca pelo título: deve retornar APENAS 1 artigo unificado
    res_search = client.get('/v2/production/article?q=redes')
    assert res_search.status_code == HTTPStatus.OK
    body_search = res_search.json()
    assert body_search['pagination']['total_items'] >= 1

    # Localiza o artigo criado
    matching = [
        a for a in body_search['data']
        if a['doi'] == doi or a['title'] == title
    ]
    assert len(matching) == 1, 'Artigo deve ser desduplicado na listagem'
    art = matching[0]

    # Verifica se os dois autores da plataforma foram unificados
    author_ids = [author['id'] for author in art['platform_authors']]
    assert str(r1.id) in author_ids
    assert str(r2.id) in author_ids
    assert art['citations_count'] == 42
    assert art['has_abstract'] is True
    assert art['has_open_access_pdf'] is True

    # Verifica evidências (matches) geradas pelo ts_headline
    assert art.get('matches') is not None
    fields = [m['field'] for m in art['matches']]
    assert 'title' in fields or 'abstract' in fields

    # 2. Detalhe pelo ID canônico
    res_detail = client.get(f"/v2/production/article/{art['id']}")
    assert res_detail.status_code == HTTPStatus.OK
    detail_body = res_detail.json()
    assert detail_body['title'] == title
    assert detail_body['abstract'] is not None
    assert 'redes complexas' in detail_body['abstract']
    assert detail_body['citations_count'] == 42
    assert detail_body['pdf_url'] == 'https://example.com/pdf'

    # 3. Detalhe pelo DOI
    res_doi = client.get(f'/v2/production/article/{doi}')
    assert res_doi.status_code == HTTPStatus.OK
    assert res_doi.json()['id'] == art['id']
