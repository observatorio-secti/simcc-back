# ruff: noqa: PLR2004, PLR0914
from http import HTTPStatus
from uuid import uuid4

import pytest
from sqlalchemy import text

# ============================================================================
# LIVROS (BOOK)
# ============================================================================


@pytest.mark.asyncio
async def test_book_validation_invalid_sort(client):
    response = client.get('/v2/production/book?by=invalid_field')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_book_detail_not_found(client):
    fake_id = uuid4()
    response = client.get(f'/v2/production/book/{fake_id}')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_book_list_structure(client):
    response = client.get('/v2/production/book?page=1&per_page=5')
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
async def test_book_deduplication_and_detail(
    client, session, researcher_factory
):
    r1 = await researcher_factory(name='Pesquisador Livro Um')
    r2 = await researcher_factory(name='Pesquisador Livro Dois')

    bp_id1 = uuid4()
    bp_id2 = uuid4()
    isbn = '978-85-1234-567-8'
    title = 'Livro Fundamental de Redes Neurais e Grafos'
    year = 2023

    await session.execute(
        text("""
        INSERT INTO bibliographic_production
            (id, researcher_id, sequence_code, title, year_, type,
             relevance, has_image)
        VALUES
            (:id1, :r1, 1, :title, :year, 'BOOK', true, false),
            (:id2, :r2, 1, :title, :year, 'BOOK', true, false);
        """),
        {
            'id1': bp_id1,
            'id2': bp_id2,
            'r1': r1.id,
            'r2': r2.id,
            'title': title,
            'year': year,
        },
    )

    await session.execute(
        text("""
        INSERT INTO bibliographic_production_book
            (id, bibliographic_production_id, isbn, publishing_company,
             publishing_company_city)
        VALUES
            (:id1, :bp_id1, :isbn, 'Editora Campus', 'Rio de Janeiro'),
            (:id2, :bp_id2, :isbn, 'Editora Campus', 'Rio de Janeiro');
        """),
        {
            'id1': uuid4(),
            'id2': uuid4(),
            'bp_id1': bp_id1,
            'bp_id2': bp_id2,
            'isbn': isbn,
        },
    )

    await session.commit()
    await session.execute(
        text('REFRESH MATERIALIZED VIEW mv_canonical_books;')
    )
    await session.commit()

    # Busca
    res_search = client.get('/v2/production/book?q=neurais')
    assert res_search.status_code == HTTPStatus.OK
    body = res_search.json()
    assert body['pagination']['total_items'] >= 1

    matching = [b for b in body['data'] if b['isbn'] == isbn]
    assert len(matching) == 1, 'Livro deve ser desduplicado'
    book = matching[0]

    author_ids = [a['id'] for a in book['platform_authors']]
    assert str(r1.id) in author_ids
    assert str(r2.id) in author_ids
    assert book['publishing_company'] == 'Editora Campus'

    # Detalhe por ID
    res_id = client.get(f"/v2/production/book/{book['id']}")
    assert res_id.status_code == HTTPStatus.OK
    detail_body = res_id.json()
    assert detail_body['title'] == title
    assert detail_body['publishing_company_city'] == 'Rio de Janeiro'

    # Detalhe por ISBN
    res_isbn = client.get(f'/v2/production/book/{isbn}')
    assert res_isbn.status_code == HTTPStatus.OK
    assert res_isbn.json()['id'] == book['id']


# ============================================================================
# CAPÍTULOS DE LIVROS (BOOK_CHAPTER)
# ============================================================================


@pytest.mark.asyncio
async def test_book_chapter_detail_not_found(client):
    fake_id = uuid4()
    response = client.get(f'/v2/production/book-chapter/{fake_id}')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_book_chapter_list_structure(client):
    response = client.get('/v2/production/book-chapter?page=1&per_page=5')
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert 'data' in body
    assert 'pagination' in body


@pytest.mark.asyncio
async def test_book_chapter_deduplication_and_detail(
    client, session, researcher_factory
):
    r1 = await researcher_factory(name='Autor Capitulo Um')
    r2 = await researcher_factory(name='Autor Capitulo Dois')

    bp_id1 = uuid4()
    bp_id2 = uuid4()
    isbn = '978-85-9876-543-2'
    title = 'Capitulo Introdutorio em Otimizacao Combinatoria'
    book_title = 'Avancos em Inteligencia Computacional'
    year = 2024

    await session.execute(
        text("""
        INSERT INTO bibliographic_production
            (id, researcher_id, sequence_code, title, year_, type,
             relevance, has_image)
        VALUES
            (:id1, :r1, 1, :title, :year, 'BOOK_CHAPTER', true, false),
            (:id2, :r2, 1, :title, :year, 'BOOK_CHAPTER', true, false);
        """),
        {
            'id1': bp_id1,
            'id2': bp_id2,
            'r1': r1.id,
            'r2': r2.id,
            'title': title,
            'year': year,
        },
    )

    await session.execute(
        text("""
        INSERT INTO bibliographic_production_book_chapter
            (id, bibliographic_production_id, isbn, book_title,
             publishing_company, organizers, start_page, end_page)
        VALUES
            (:id1, :bp_id1, :isbn, :book_title, 'Springer', 'Silva et al',
             '10', '25'),
            (:id2, :bp_id2, :isbn, :book_title, 'Springer', 'Silva et al',
             '10', '25');
        """),
        {
            'id1': uuid4(),
            'id2': uuid4(),
            'bp_id1': bp_id1,
            'bp_id2': bp_id2,
            'isbn': isbn,
            'book_title': book_title,
        },
    )

    await session.commit()
    await session.execute(
        text('REFRESH MATERIALIZED VIEW mv_canonical_book_chapters;')
    )
    await session.commit()

    # Busca
    res_search = client.get('/v2/production/book-chapter?q=otimizacao')
    assert res_search.status_code == HTTPStatus.OK
    body = res_search.json()
    assert body['pagination']['total_items'] >= 1

    matching = [c for c in body['data'] if c['isbn'] == isbn]
    assert len(matching) == 1, 'Capitulo deve ser desduplicado'
    chapter = matching[0]

    author_ids = [a['id'] for a in chapter['platform_authors']]
    assert str(r1.id) in author_ids
    assert str(r2.id) in author_ids
    assert chapter['book_title'] == book_title

    # Detalhe por ID
    res_id = client.get(f"/v2/production/book-chapter/{chapter['id']}")
    assert res_id.status_code == HTTPStatus.OK
    detail_body = res_id.json()
    assert detail_body['title'] == title
    assert detail_body['organizers'] == 'Silva et al'
    assert detail_body['start_page'] == '10'

    # Detalhe por ISBN
    res_isbn = client.get(f'/v2/production/book-chapter/{isbn}')
    assert res_isbn.status_code == HTTPStatus.OK
    assert res_isbn.json()['id'] == chapter['id']


# ============================================================================
# SOFTWARES (SOFTWARE)
# ============================================================================


@pytest.mark.asyncio
async def test_software_detail_not_found(client):
    fake_id = uuid4()
    response = client.get(f'/v2/production/software/{fake_id}')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_software_list_structure(client):
    response = client.get('/v2/production/software?page=1&per_page=5')
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert 'data' in body
    assert 'pagination' in body


@pytest.mark.asyncio
async def test_software_deduplication_and_detail(
    client, session, researcher_factory
):
    r1 = await researcher_factory(name='Dev Software Um')
    r2 = await researcher_factory(name='Dev Software Dois')

    code = 'SW-2024-TEST-99'
    title = 'Simulador de Dinamica de Fluidos em Tempo Real'
    year = 2024

    await session.execute(
        text("""
        INSERT INTO software
            (id, researcher_id, sequence_code, title, year, platform,
             environment, code, availability, financing_institutionc)
        VALUES
            (:id1, :r1, 1, :title, :year, 'Web', 'Docker/Python', :code,
             'Restrita', 'FAPEMIG'),
            (:id2, :r2, 1, :title, :year, 'Web', 'Docker/Python', :code,
             'Restrita', 'FAPEMIG');
        """),
        {
            'id1': uuid4(),
            'id2': uuid4(),
            'r1': r1.id,
            'r2': r2.id,
            'title': title,
            'year': year,
            'code': code,
        },
    )

    await session.commit()
    await session.execute(
        text('REFRESH MATERIALIZED VIEW mv_canonical_software;')
    )
    await session.commit()

    # Busca
    res_search = client.get('/v2/production/software?q=fluidos')
    assert res_search.status_code == HTTPStatus.OK
    body = res_search.json()
    assert body['pagination']['total_items'] >= 1

    matching = [s for s in body['data'] if s['code'] == code]
    assert len(matching) == 1, 'Software deve ser desduplicado'
    sw = matching[0]

    author_ids = [a['id'] for a in sw['platform_authors']]
    assert str(r1.id) in author_ids
    assert str(r2.id) in author_ids
    assert sw['platform'] == 'Web'

    # Detalhe por ID
    res_id = client.get(f"/v2/production/software/{sw['id']}")
    assert res_id.status_code == HTTPStatus.OK
    detail_body = res_id.json()
    assert detail_body['title'] == title
    assert detail_body['financing'] == 'FAPEMIG'
    assert detail_body['availability'] == 'Restrita'

    # Detalhe por Código
    res_code = client.get(f'/v2/production/software/{code}')
    assert res_code.status_code == HTTPStatus.OK
    assert res_code.json()['id'] == sw['id']


# ============================================================================
# PATENTES (PATENT)
# ============================================================================


@pytest.mark.asyncio
async def test_patent_detail_not_found(client):
    fake_id = uuid4()
    response = client.get(f'/v2/production/patent/{fake_id}')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_patent_list_structure(client):
    response = client.get('/v2/production/patent?page=1&per_page=5')
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert 'data' in body
    assert 'pagination' in body


@pytest.mark.asyncio
async def test_patent_deduplication_and_detail(
    client, session, researcher_factory
):
    r1 = await researcher_factory(name='Inventor Um')
    r2 = await researcher_factory(name='Inventor Dois')

    code = 'BR 10 2024 000123 4'
    title = 'Dispositivo Microcontrolado para Monitoramento Remoto'
    dev_year = '2024'

    await session.execute(
        text("""
        INSERT INTO patent
            (id, researcher_id, sequence_code, title, category,
             development_year, details, code, deposit_date)
        VALUES
            (:id1, :r1, 1, :title, 'Invenção', :dev_year,
             'Detalhes tecnicos do microcontrolador', :code, '10/01/2024'),
            (:id2, :r2, 1, :title, 'Invenção', :dev_year,
             'Detalhes tecnicos do microcontrolador', :code, '10/01/2024');
        """),
        {
            'id1': uuid4(),
            'id2': uuid4(),
            'r1': r1.id,
            'r2': r2.id,
            'title': title,
            'dev_year': dev_year,
            'code': code,
        },
    )

    await session.commit()
    await session.execute(
        text('REFRESH MATERIALIZED VIEW mv_canonical_patents;')
    )
    await session.commit()

    # Busca
    res_search = client.get('/v2/production/patent?q=microcontrolado')
    assert res_search.status_code == HTTPStatus.OK
    body = res_search.json()
    assert body['pagination']['total_items'] >= 1

    matching = [p for p in body['data'] if p['code'] == code]
    assert len(matching) == 1, 'Patente deve ser desduplicada'
    pat = matching[0]

    author_ids = [a['id'] for a in pat['platform_authors']]
    assert str(r1.id) in author_ids
    assert str(r2.id) in author_ids
    assert pat['category'] == 'Invenção'

    # Detalhe por ID
    res_id = client.get(f"/v2/production/patent/{pat['id']}")
    assert res_id.status_code == HTTPStatus.OK
    detail_body = res_id.json()
    assert detail_body['title'] == title
    assert detail_body['details'] == 'Detalhes tecnicos do microcontrolador'

    # Detalhe por Código
    res_code = client.get(f'/v2/production/patent/{code}')
    assert res_code.status_code == HTTPStatus.OK
    assert res_code.json()['id'] == pat['id']


# ============================================================================
# EVENTOS (PARTICIPATION_EVENT)
# ============================================================================


@pytest.mark.asyncio
async def test_event_detail_not_found(client):
    fake_id = uuid4()
    response = client.get(f'/v2/production/event/{fake_id}')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_event_list_structure(client):
    response = client.get('/v2/production/event?page=1&per_page=5')
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert 'data' in body
    assert 'pagination' in body


@pytest.mark.asyncio
async def test_event_deduplication_and_detail(
    client, session, researcher_factory
):
    r1 = await researcher_factory(name='Participante Um')
    r2 = await researcher_factory(name='Participante Dois')

    title = 'Apresentacao de Trabalho sobre Grafos Semanticos'
    event_name = 'Congresso Brasileiro de Informatica'
    year = 2024

    await session.execute(
        text("""
        INSERT INTO participation_events
            (id, researcher_id, sequence_code, title, event_name, nature,
             form_participation, type_participation, year)
        VALUES
            (:id1, :r1, 1, :title, :event_name, 'Nacional', 'Oral',
             'Participante Convidado', :year),
            (:id2, :r2, 1, :title, :event_name, 'Nacional', 'Oral',
             'Participante Convidado', :year);
        """),
        {
            'id1': uuid4(),
            'id2': uuid4(),
            'r1': r1.id,
            'r2': r2.id,
            'title': title,
            'event_name': event_name,
            'year': year,
        },
    )

    await session.commit()
    await session.execute(
        text('REFRESH MATERIALIZED VIEW mv_canonical_events;')
    )
    await session.commit()

    # Busca
    res_search = client.get('/v2/production/event?q=semanticos')
    assert res_search.status_code == HTTPStatus.OK
    body = res_search.json()
    assert body['pagination']['total_items'] >= 1

    matching = [e for e in body['data'] if e['title'] == title]
    assert len(matching) == 1, 'Evento deve ser desduplicado'
    ev = matching[0]

    author_ids = [a['id'] for a in ev['platform_authors']]
    assert str(r1.id) in author_ids
    assert str(r2.id) in author_ids
    assert ev['event_name'] == event_name

    # Detalhe por ID
    res_id = client.get(f"/v2/production/event/{ev['id']}")
    assert res_id.status_code == HTTPStatus.OK
    detail_body = res_id.json()
    assert detail_body['title'] == title
    assert detail_body['nature'] == 'Nacional'
    assert detail_body['form_participation'] == 'Oral'
    assert detail_body['type_participation'] == 'Participante Convidado'


# ============================================================================
# PROJETOS DE PESQUISA (RESEARCH_PROJECT)
# ============================================================================


@pytest.mark.asyncio
async def test_research_project_detail_not_found(client):
    fake_id = uuid4()
    response = client.get(f'/v2/production/research-project/{fake_id}')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_research_project_list_structure(client):
    response = client.get('/v2/production/research-project?page=1&per_page=5')
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert 'data' in body
    assert 'pagination' in body


@pytest.mark.asyncio
async def test_research_project_unknown_param(client):
    response = client.get('/v2/production/research-project?qualis=A1')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_research_project_deduplication_and_detail(
    client, session, researcher_factory
):
    r1 = await researcher_factory(name='Integrante Projeto Um')
    r2 = await researcher_factory(name='Integrante Projeto Dois')

    rp_id1 = uuid4()
    rp_id2 = uuid4()
    title = 'Projeto de Aprendizado Federado em Saude Publica'

    await session.execute(
        text("""
        INSERT INTO research_project
            (id, researcher_id, sequence_code, start_year, end_year,
             agency_name, project_name, status, nature, number_phd,
             description)
        VALUES
            (:id1, :r1, 1, 2022, NULL, 'CNPq', :title, 'EM_ANDAMENTO',
             'PESQUISA', 2, 'Estudo sobre privacidade diferencial'),
            (:id2, :r2, 1, 2022, NULL, 'CNPq', :title, 'EM_ANDAMENTO',
             'PESQUISA', 2, 'Estudo sobre privacidade diferencial');
        """),
        {
            'id1': rp_id1,
            'id2': rp_id2,
            'r1': r1.id,
            'r2': r2.id,
            'title': title,
        },
    )
    await session.execute(
        text("""
        INSERT INTO research_project_foment
            (project_id, agency_name, agency_code, nature)
        VALUES
            (:id1, 'CNPq', '002200', 'Auxílio financeiro'),
            (:id2, 'CNPq', '002200', 'Auxílio financeiro');
        """),
        {'id1': rp_id1, 'id2': rp_id2},
    )
    await session.execute(
        text("""
        INSERT INTO research_project_components
            (id, project_id, name, lattes_id, coordinator)
        VALUES
            (:c1, :id1, 'Integrante Projeto Um', '1111', true),
            (:c2, :id1, 'Integrante Projeto Dois', '2222', false),
            (:c3, :id2, 'Integrante Projeto Um', '1111', true),
            (:c4, :id2, 'Integrante Projeto Dois', '2222', false);
        """),
        {
            'c1': uuid4(),
            'c2': uuid4(),
            'c3': uuid4(),
            'c4': uuid4(),
            'id1': rp_id1,
            'id2': rp_id2,
        },
    )

    await session.commit()
    await session.execute(
        text('REFRESH MATERIALIZED VIEW mv_canonical_research_projects;')
    )
    await session.commit()

    # Busca
    res_search = client.get(
        '/v2/production/research-project?q=federado'
        '&status=EM_ANDAMENTO&facets=status,nature'
    )
    assert res_search.status_code == HTTPStatus.OK
    body = res_search.json()
    assert body['pagination']['total_items'] >= 1
    assert body['facets']['status']['items'][0]['value'] == 'EM_ANDAMENTO'

    matching = [p for p in body['data'] if p['title'] == title]
    assert len(matching) == 1, 'Projeto deve ser desduplicado'
    project = matching[0]

    author_ids = [a['id'] for a in project['platform_authors']]
    assert str(r1.id) in author_ids
    assert str(r2.id) in author_ids
    assert project['start_year'] == 2022
    assert project['agency_name'] == 'CNPq'

    # Filtro que exclui o projeto
    res_done = client.get(
        '/v2/production/research-project?q=federado&status=CONCLUIDO'
    )
    assert res_done.json()['pagination']['total_items'] == 0

    # Detalhe pelo ID de qualquer cópia
    res_id = client.get(f'/v2/production/research-project/{rp_id2}')
    assert res_id.status_code == HTTPStatus.OK
    detail = res_id.json()
    assert detail['id'] == project['id']
    assert detail['number_phd'] == 2
    assert len(detail['foment']) == 1
    assert detail['foment'][0]['agency_code'] == '002200'
    assert len(detail['components']) == 2
    coordinators = [c for c in detail['components'] if c['coordinator']]
    assert coordinators[0]['lattes_id'] == '1111'
