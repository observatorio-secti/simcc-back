# ruff: noqa: PLR2004
"""Testes do endpoint `GET /v2/metrics/general`."""

import uuid
from http import HTTPStatus

import pytest
from sqlalchemy import text

from simcc.v2.dependencies import get_search_cache


class _InMemoryCache:
    def __init__(self):
        self.store = {}

    @staticmethod
    async def build_key(context, params):
        return f'v2:{context}'

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value):
        self.store[key] = value


async def _refresh(session, view: str) -> None:
    await session.commit()
    await session.execute(text(f'REFRESH MATERIALIZED VIEW {view};'))
    await session.commit()


@pytest.mark.asyncio
async def test_general_metrics_empty(client):
    response = client.get('/v2/metrics/general')

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['data'] == {
        'articles': 0,
        'books': 0,
        'book_chapters': 0,
        'work_in_event': 0,
        'patents': 0,
        'software': 0,
        'brands': 0,
        'researchers': 0,
    }
    assert body['meta']['cached'] is False


@pytest.mark.asyncio
async def test_general_metrics_counts_unique_productions_and_cache(
    client, session, researcher_factory
):
    r1 = await researcher_factory(name='Pesquisador Um')
    r2 = await researcher_factory(name='Pesquisador Dois')
    mag_id = uuid.uuid4()
    await session.execute(
        text(
            'INSERT INTO periodical_magazine (id, name, issn, qualis) '
            "VALUES (:id, 'Revista Teste', '1234-5678', 'A1')"
        ),
        {'id': mag_id},
    )

    # Mesmo artigo (mesmo DOI e título) para dois pesquisadores: deve contar 1
    for idx, researcher in enumerate((r1, r2)):
        prod_id = uuid.uuid4()
        await session.execute(
            text(
                'INSERT INTO bibliographic_production '
                '(id, sequence_code, title, type, year, year_, '
                'researcher_id, doi) '
                "VALUES (:id, :seq, 'Artigo Coautoria', 'ARTICLE', '2024', "
                "2024, :r, '10.1000/shared')"
            ),
            {'id': prod_id, 'seq': idx, 'r': researcher.id},
        )
        await session.execute(
            text(
                'INSERT INTO bibliographic_production_article '
                '(bibliographic_production_id, periodical_magazine_id, qualis) '
                'VALUES (:id, :mag_id, :qualis)'
            ),
            {'id': prod_id, 'mag_id': mag_id, 'qualis': 'A1'},
        )

    await session.execute(
        text(
            'INSERT INTO patent '
            '(id, sequence_code, title, development_year, researcher_id) '
            "VALUES (:id, 1, 'Patente Unica', '2023', :r)"
        ),
        {'id': uuid.uuid4(), 'r': r1.id},
    )

    await _refresh(session, 'mv_canonical_articles')
    await _refresh(session, 'mv_canonical_patents')

    fake_cache = _InMemoryCache()
    client.app.dependency_overrides[get_search_cache] = lambda: fake_cache
    try:
        first = client.get('/v2/metrics/general')
        assert first.status_code == HTTPStatus.OK
        first_body = first.json()
        assert first_body['data'] == {
            'articles': 1,
            'books': 0,
            'book_chapters': 0,
            'work_in_event': 0,
            'patents': 1,
            'software': 0,
            'brands': 0,
            'researchers': 2,
        }
        assert first_body['meta']['cached'] is False

        second = client.get('/v2/metrics/general')
        assert second.status_code == HTTPStatus.OK
        second_body = second.json()
        assert second_body['data'] == first_body['data']
        assert second_body['meta']['cached'] is True
    finally:
        client.app.dependency_overrides.pop(get_search_cache, None)
