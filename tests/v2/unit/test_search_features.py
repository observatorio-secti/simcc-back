# ruff: noqa: PLR2004
from http import HTTPStatus

import pytest
from sqlalchemy import event

from simcc.core.db.models.production import Software
from simcc.v2.services.mv_refresh_service import (
    refresh_search_materialized_views,
)


@pytest.mark.asyncio
async def test_validation_sort_by_relevance_requires_q(client):
    response = client.get('/v2/researcher?sort_by=relevance')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert 'relevance' in response.json()['detail']


@pytest.mark.asyncio
async def test_validation_include_matches_requires_q(client):
    response = client.get('/v2/researcher?include=matches')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert 'matches' in response.json()['detail']


@pytest.mark.asyncio
async def test_validation_include_matches_per_page_limit(client):
    response = client.get('/v2/researcher?q=AI&include=matches&per_page=51')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert 'per_page <= 50' in response.json()['detail']


@pytest.mark.asyncio
async def test_validation_invalid_facet(client):
    response = client.get('/v2/researcher?facets=unknown_facet')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_validation_invalid_include(client):
    response = client.get('/v2/researcher?include=unknown_include')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_full_text_search_profile_unaccent(client, researcher_factory):
    await researcher_factory(
        name='Sebastião Salgado',
        abstract=(
            'Especialista em inteligência artificial e visão '
            'computacional avançada.'
        ),
    )
    await researcher_factory(
        name='Maria Pereira',
        abstract='Pesquisadora na área de linguística histórica.',
    )

    # Busca com acentuação diferente: "visao computacional"
    res = client.get('/v2/researcher?q=visao computacional')
    assert res.status_code == HTTPStatus.OK
    body = res.json()
    assert len(body['data']) == 1
    assert body['data'][0]['name'] == 'Sebastião Salgado'


@pytest.mark.asyncio
async def test_full_text_search_production_document_and_matches(
    client, session, researcher_factory
):
    r1 = await researcher_factory(name='Ada Lovelace')
    await researcher_factory(name='Charles Babbage')

    # Adiciona um software na produção de Ada Lovelace
    sw = Software(
        researcher_id=r1.id,
        title='Simulador Algébrico de Máquinas Analíticas',
        year=2021,
    )
    session.add(sw)
    await session.commit()
    await refresh_search_materialized_views(session, concurrently=False)

    # Busca por "simulador algebrico" deve achar Ada Lovelace via Camada 1
    res = client.get('/v2/researcher?q=simulador algebrico&include=matches')
    assert res.status_code == HTTPStatus.OK
    body = res.json()
    assert len(body['data']) == 1
    item = body['data'][0]
    assert item['researcher_id'] == str(r1.id)

    # Valida estrutura de matches
    assert item['matches'] is not None
    assert item['matches']['total'] >= 1
    assert 'SOFTWARE' in item['matches']['by_type']
    assert len(item['matches']['items']) >= 1
    first_match = item['matches']['items'][0]
    assert first_match['source_type'] == 'SOFTWARE'
    assert 'Simulador' in first_match['title']
    # Snippet com destaque [[...]]
    assert '[[' in first_match['snippet']
    assert ']]' in first_match['snippet']


@pytest.mark.asyncio
async def test_disjunctive_facets(
    client, researcher_factory, institution_factory
):
    inst1 = await institution_factory(name='Instituto Alpha', acronym='IA')
    inst2 = await institution_factory(name='Instituto Beta', acronym='IB')

    await researcher_factory(
        name='Pesquisador Disjuntivo Alpha', institution_id=inst1.id
    )
    await researcher_factory(
        name='Pesquisador Disjuntivo Beta', institution_id=inst2.id
    )

    # Filtrar por q=Disjuntivo e institution_id=inst1.id com facets=institution
    res = client.get(
        f'/v2/researcher?q=Disjuntivo&institution_id={inst1.id}'
        '&facets=institution'
    )
    assert res.status_code == HTTPStatus.OK
    body = res.json()

    # Resultados filtrados apenas contêm inst1
    assert len(body['data']) == 1
    assert body['data'][0]['name'] == 'Pesquisador Disjuntivo Alpha'

    # Mas o facet de instituições é DISJUNTIVO (mostra inst1 e inst2)
    assert body['facets'] is not None
    assert 'institution' in body['facets']
    facet_values = [f['value'] for f in body['facets']['institution']]
    assert str(inst1.id) in facet_values
    assert str(inst2.id) in facet_values


@pytest.mark.asyncio
async def test_query_count_budget(client, session, researcher_factory, engine):
    await researcher_factory(name='Query Budget Test Researcher')

    query_statements = []

    def count_queries(*args, **kwargs):
        statement = args[2] if len(args) > 2 else kwargs.get('statement', '')
        upper_stmt = statement.strip().upper()
        if upper_stmt.startswith('SELECT') or upper_stmt.startswith('WITH'):
            query_statements.append(statement)

    event.listen(engine.sync_engine, 'before_cursor_execute', count_queries)

    try:
        # 1. Busca básica: exatamente 2 queries (count + page)
        query_statements.clear()
        res_basic = client.get('/v2/researcher')
        assert res_basic.status_code == HTTPStatus.OK
        assert len(query_statements) == 2

        # 2. Busca com include=matches: +2 queries (total 4 queries)
        query_statements.clear()
        res_matches = client.get('/v2/researcher?q=Budget&include=matches')
        assert res_matches.status_code == HTTPStatus.OK
        assert len(query_statements) == 4

        # 3. Busca com 1 facet: +1 query (total 3 queries)
        query_statements.clear()
        res_facet = client.get('/v2/researcher?facets=institution')
        assert res_facet.status_code == HTTPStatus.OK
        assert len(query_statements) == 3

        # 4. Busca com 2 facets: +2 queries (total 4 queries)
        query_statements.clear()
        res_2facets = client.get('/v2/researcher?facets=institution,year')
        assert res_2facets.status_code == HTTPStatus.OK
        assert len(query_statements) == 4

        # 5. Busca com 1 facet + include=matches: 2 + 1 + 2 = 5 queries
        query_statements.clear()
        res_combo = client.get(
            '/v2/researcher?q=Budget&facets=institution&include=matches'
        )
        assert res_combo.status_code == HTTPStatus.OK
        assert len(query_statements) == 5

    finally:
        event.remove(
            engine.sync_engine, 'before_cursor_execute', count_queries
        )


@pytest.mark.asyncio
async def test_relevance_ranking_by_production_volume(
    client, session, researcher_factory
):
    r_few = await researcher_factory(name='Pesquisador Poucas Ocorrências')
    sw1 = Software(
        researcher_id=r_few.id,
        title='Sistema de monitoramento de Dengue em áreas urbanas',
        year=2022,
    )
    session.add(sw1)

    r_many = await researcher_factory(name='Pesquisador Muitas Ocorrências')
    for i in range(3):
        sw = Software(
            researcher_id=r_many.id,
            title=f'Epidemiologia e controle da Dengue volume {i}',
            year=2020 + i,
        )
        session.add(sw)

    await session.commit()
    await refresh_search_materialized_views(session, concurrently=False)

    res = client.get('/v2/researcher?q=Dengue&sort_by=relevance')
    assert res.status_code == HTTPStatus.OK
    body = res.json()
    assert body['sort']['by'] == 'relevance'
    assert body['sort']['order'] == 'desc'

    ids = [item['researcher_id'] for item in body['data']]
    assert str(r_many.id) in ids
    assert str(r_few.id) in ids
    assert ids.index(str(r_many.id)) < ids.index(str(r_few.id))
