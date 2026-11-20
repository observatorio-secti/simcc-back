# ruff: noqa: PLR2004
"""Contrato v2 — Fase 2: Qualis/JCR, revistas, bolsistas, termos e
indicadores."""

import uuid
from http import HTTPStatus

import pytest
from sqlalchemy import text

from simcc.v2.schemas.production import ArticleDetail, MagazineRef
from simcc.v2.schemas.qualis import parse_jcr, parse_qualis


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('A1', ('A1', None)),
        (' b2 ', ('B2', None)),
        ('SQ', (None, 'not_rated')),
        ('NP', (None, 'not_applicable')),
        ('None', (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_qualis(raw, expected):
    assert parse_qualis(raw) == expected


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [('2,345', 2.345), ('1.5', 1.5), ('n/d', None), (None, None), (3, 3.0)],
)
def test_parse_jcr(raw, expected):
    assert parse_jcr(raw) == expected


def test_magazine_ref_types_values_from_database():
    ref = MagazineRef(name='Rev', qualis='SQ', jcr='1,25')

    assert ref.qualis is None
    assert ref.qualis_status == 'not_rated'
    assert ref.jcr == 1.25


def test_article_detail_splits_authors_and_keywords():
    detail = ArticleDetail(
        id=uuid.uuid4(),
        title='T',
        keywords=['redes', 'grafos'],
        all_authors_raw='SILVA, A.; SOUZA, B. ; ',
    )

    assert [a.name for a in detail.authors] == ['SILVA, A.', 'SOUZA, B.']


async def _magazines(session):
    for name, issn, qualis, jcr in (
        ('Revista Alfa', '1111-1111', 'A1', '3,5'),
        ('Revista Beta', '2222-2222', 'B2', '0.8'),
        ('Revista Gama', '3333-3333', 'SQ', None),
    ):
        await session.execute(
            text(
                'INSERT INTO periodical_magazine (name, issn, qualis, jcr) '
                'VALUES (:n, :i, :q, :j)'
            ),
            {'n': name, 'i': issn, 'q': qualis, 'j': jcr},
        )
    await session.commit()


@pytest.mark.asyncio
async def test_magazine_list_filters_sort_and_facets(client, session):
    await _magazines(session)

    body = client.get(
        '/v2/magazine?q=Revista&sort_by=jcr&facets=qualis'
    ).json()
    names = [m['name'] for m in body['data']]
    assert names[:2] == ['Revista Alfa', 'Revista Beta']
    assert body['data'][0]['jcr'] == 3.5
    assert body['sort'] == {'by': 'jcr', 'order': 'desc'}
    facet_values = {i['value'] for i in body['facets']['qualis']['items']}
    assert facet_values == {'A1', 'B2', 'not_rated'}

    not_rated = client.get('/v2/magazine?qualis=SQ').json()['data']
    assert [m['name'] for m in not_rated] == ['Revista Gama']
    assert not_rated[0]['qualis'] is None
    assert not_rated[0]['qualis_status'] == 'not_rated'

    by_issn = client.get('/v2/magazine?issn=2222-2222').json()['data']
    detail = client.get(f'/v2/magazine/{by_issn[0]["id"]}').json()['data']
    assert detail['qualis'] == 'B2'

    missing = client.get(f'/v2/magazine/{uuid.uuid4()}')
    assert missing.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_scholarship_filters_and_facets(
    client, session, researcher_factory
):
    r1 = await researcher_factory(name='Bolsista Um')
    r2 = await researcher_factory(name='Bolsista Dois')
    for seq, (rid, level) in enumerate(((r1.id, '1A'), (r2.id, '2'))):
        await session.execute(
            text(
                'INSERT INTO foment (researcher_id, sequence_code, '
                'modality_name, category_level_code, scholarship_quantity) '
                "VALUES (:r, :s, 'Produtividade em Pesquisa', :l, 1)"
            ),
            {'r': rid, 's': seq, 'l': level},
        )
    await session.commit()

    body = client.get(
        '/v2/scholarship?facets=category_level&category_level=1A'
    ).json()
    assert [s['researcher']['name'] for s in body['data']] == ['Bolsista Um']
    levels = {i['value'] for i in body['facets']['category_level']['items']}
    assert {'1A', '2'} <= levels

    by_researcher = client.get(
        f'/v2/scholarship?researcher_id={r2.id}'
    ).json()
    assert by_researcher['data'][0]['category_level'] == '2'


@pytest.mark.asyncio
async def test_researcher_terms_and_production_metric(
    client, session, researcher_factory
):
    researcher = await researcher_factory(name='Termos Autor')
    for seq, (title, year) in enumerate(
        (
            ('Aprendizado de máquina na saúde', 2020),
            ('Aprendizado profundo para imagens', 2021),
            ('Marca de aprendizado', 2021),
        )
    ):
        await session.execute(
            text(
                'INSERT INTO brand (researcher_id, sequence_code, title, '
                'year) VALUES (:r, :s, :t, :y)'
            ),
            {'r': researcher.id, 's': seq, 't': title, 'y': year},
        )
    await session.commit()
    await session.execute(
        text('REFRESH MATERIALIZED VIEW mv_canonical_brands')
    )
    await session.commit()

    terms = client.get(f'/v2/researcher/{researcher.id}/terms?limit=3')
    assert terms.status_code == HTTPStatus.OK
    first = terms.json()['data'][0]
    assert first == {'term': 'aprendizado', 'frequency': 3}
    assert all(t['term'] != 'para' for t in terms.json()['data'])

    metric = client.get(
        f'/v2/metrics/production/brand?researcher_id={researcher.id}'
    ).json()
    assert metric['kind'] == 'brand'
    assert metric['data'] == [
        {'period': 2020, 'value': 1},
        {'period': 2021, 'value': 2},
    ]

    hyphen = client.get('/v2/metrics/production/book-chapter')
    assert hyphen.status_code == HTTPStatus.OK
    assert hyphen.json()['kind'] == 'book_chapter'

    invalid = client.get('/v2/metrics/production/poem')
    assert invalid.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
