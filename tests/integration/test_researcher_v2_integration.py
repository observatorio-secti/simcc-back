from http import HTTPStatus
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.repositories.researcher_repo import fetch_researchers_v2

PAGE_DEFAULT = 1
PER_PAGE_DEFAULT = 20
PER_PAGE_CUSTOM = 5
MIN_EXPECTED_ITEMS = 2

VALID_SOURCES = {
    'ARTICLE',
    'BOOK',
    'BOOK_CHAPTER',
    'PATENT',
    'SOFTWARE',
}

VALID_FIELDS = {'title', 'abstract', 'name', 'keywords'}


@pytest_asyncio.fixture(scope='module', autouse=True)
async def setup_test_materialized_views(engine):
    """Cria extensões, visão materializada e dados base para os testes."""
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS unaccent;'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm;'))
        await conn.execute(
            text("""
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_ts_config WHERE cfgname = 'pt_unaccent'
          ) THEN
            CREATE TEXT SEARCH CONFIGURATION pt_unaccent ( COPY = portuguese );
            ALTER TEXT SEARCH CONFIGURATION pt_unaccent
              ALTER MAPPING FOR hword, hword_part, word
              WITH unaccent, portuguese_stem;
          END IF;
        END $$;
        """)
        )
        await conn.execute(
            text("""
        INSERT INTO researcher (id, name, lattes_id, status)
        VALUES
            ('11111111-1111-1111-1111-111111111111',
             'Pesquisador Alfa Computacao', '1111222233334444', TRUE),
            ('22222222-2222-2222-2222-222222222222',
             'Pesquisador Beta Inteligencia', '5555666677778888', TRUE)
        ON CONFLICT (id) DO NOTHING;
        """)
        )
        await conn.execute(
            text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_researcher_search AS
        SELECT
            r.id AS researcher_id,
            r.name,
            r.institution_id,
            '{}'::uuid[] AS graduate_program_ids,
            '{}'::int[] AS production_years,
            to_tsvector('pt_unaccent', coalesce(r.name, '')) AS search_vector
        FROM researcher r
        WHERE r.status = TRUE;
        """)
        )
        await conn.execute(
            text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_researcher_test_id
        ON mv_researcher_search (researcher_id);
        """)
        )
        await conn.execute(
            text('REFRESH MATERIALIZED VIEW mv_researcher_search;')
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_researchers_v2_endpoint_success(async_client):
    """Garante que GET /v2/researcher responde 200 com envelope padronizado."""
    response = await async_client.get('/v2/researcher')

    assert response.status_code == HTTPStatus.OK
    body = response.json()

    # Valida estrutura do envelope
    assert 'data' in body
    assert 'pagination' in body
    assert 'sort' in body
    assert 'meta' in body

    # Valida metadados de paginação
    pagination = body['pagination']
    assert pagination['total_items'] >= MIN_EXPECTED_ITEMS
    assert pagination['page'] == PAGE_DEFAULT
    assert pagination['per_page'] == PER_PAGE_DEFAULT
    assert pagination['has_prev'] is False

    # Valida itens retornados
    assert len(body['data']) > 0
    first_item = body['data'][0]
    assert 'name' in first_item
    assert isinstance(first_item['name'], str)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_researchers_v2_with_search_query(async_client):
    """Valida busca textual por termo q."""
    response = await async_client.get('/v2/researcher?q=Computacao')

    assert response.status_code == HTTPStatus.OK
    body = response.json()

    assert body['pagination']['total_items'] >= 1
    assert len(body['data']) >= 1

    matched = any('Computacao' in r['name'] for r in body['data'])
    assert matched is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_researchers_v2_pagination_controls(async_client):
    """Valida controles de paginação (page, per_page, has_prev, has_next)."""
    response = await async_client.get(
        f'/v2/researcher?page={PAGE_DEFAULT}&per_page=1'
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()

    assert len(body['data']) == 1
    assert body['pagination']['page'] == PAGE_DEFAULT
    assert body['pagination']['per_page'] == 1
    assert body['pagination']['has_next'] is True
    assert body['pagination']['has_prev'] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_researcher_repo_fallback_safe_rollback(session: AsyncSession):
    """Garante fallback seguro para ORM caso a MV não seja utilizada."""
    query_params = {
        'filters': {'q': None},
        'pagination': {'page': PAGE_DEFAULT, 'per_page': PER_PAGE_CUSTOM},
        'sort': {'by': 'name', 'order': 'asc'},
    }

    # Simula indisponibilidade da MV para validar o fallback
    with patch(
        'simcc.v2.repositories.researcher_repo._fetch_from_mv',
        return_value=None,
    ):
        records, total = await fetch_researchers_v2(
            session=session,
            query_params=query_params,
        )

        assert total >= MIN_EXPECTED_ITEMS
        assert len(records) >= MIN_EXPECTED_ITEMS
