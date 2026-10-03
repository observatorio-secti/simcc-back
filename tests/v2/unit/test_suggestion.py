# ruff: noqa: PLR2004
from http import HTTPStatus

import pytest

from simcc.core.db.models.miscellaneous import ResearchDictionary


@pytest.fixture
def dictionary_factory(session):
    async def create(term, frequency, type_='ARTICLE'):
        session.add(
            ResearchDictionary(term=term, frequency=frequency, type_=type_)
        )
        await session.flush()

    return create


def terms(response):
    return [item['term'] for item in response.json()['data']]


@pytest.mark.asyncio
async def test_suggestions_match_prefix_ordered_by_frequency(
    client, dictionary_factory
):
    await dictionary_factory('educacional', 40)
    await dictionary_factory('educação', 900)
    await dictionary_factory('educação infantil', 120)
    await dictionary_factory('reeducação', 500)

    response = client.get('/v2/suggestion?q=educ')

    assert response.status_code == HTTPStatus.OK
    assert terms(response) == ['educação', 'educação infantil', 'educacional']
    assert response.json()['data'][0]['frequency'] == 900


@pytest.mark.asyncio
async def test_suggestions_ignore_accents_and_case(client, dictionary_factory):
    await dictionary_factory('educação', 900)

    assert terms(client.get('/v2/suggestion?q=EDUCAÇ')) == ['educação']
    assert terms(client.get('/v2/suggestion?q=educac')) == ['educação']


@pytest.mark.asyncio
async def test_suggestions_sum_frequency_across_types(
    client, dictionary_factory
):
    await dictionary_factory('saúde', 10, 'ARTICLE')
    await dictionary_factory('saúde', 5, 'BOOK')
    await dictionary_factory('saúde pública', 12, 'ARTICLE')

    body = client.get('/v2/suggestion?q=sau').json()

    assert body['data'] == [
        {
            'term': 'saúde',
            'frequency': 15,
            'source_types': ['ARTICLE', 'BOOK'],
        },
        {
            'term': 'saúde pública',
            'frequency': 12,
            'source_types': ['ARTICLE'],
        },
    ]


@pytest.mark.asyncio
async def test_suggestions_filter_by_source_type(client, dictionary_factory):
    await dictionary_factory('saúde', 10, 'ARTICLE')
    await dictionary_factory('saúde', 5, 'BOOK')
    await dictionary_factory('saneamento', 7, 'PATENT')

    body = client.get(
        '/v2/suggestion?q=sa&source_type=BOOK&source_type=PATENT'
    ).json()

    assert body['data'] == [
        {'term': 'saneamento', 'frequency': 7, 'source_types': ['PATENT']},
        {'term': 'saúde', 'frequency': 5, 'source_types': ['BOOK']},
    ]


@pytest.mark.asyncio
async def test_suggestions_respect_limit(client, dictionary_factory):
    for index in range(5):
        await dictionary_factory(f'termo {index}', 10 + index)

    assert len(terms(client.get('/v2/suggestion?q=termo&limit=3'))) == 3


@pytest.mark.asyncio
async def test_like_wildcards_are_literal(client, dictionary_factory):
    await dictionary_factory('educação', 900)

    assert terms(client.get('/v2/suggestion?q=%25')) == []
    assert terms(client.get('/v2/suggestion?q=e_uc')) == []


@pytest.mark.asyncio
async def test_second_request_is_served_from_cache(client, dictionary_factory):
    await dictionary_factory('educação', 900)

    first = client.get('/v2/suggestion?q=educ').json()
    second = client.get('/v2/suggestion?q=EDUC').json()

    assert first['meta']['cached'] is False
    assert second['meta']['cached'] is True
    assert second['data'] == first['data']


@pytest.mark.parametrize(
    'query',
    [
        '',
        '?q=',
        '?q=%20%20',
        '?q=educ&limit=0',
        '?q=educ&limit=101',
        '?q=educ&source_type=INVALID',
        '?q=educ&unknown=1',
    ],
)
def test_invalid_params_return_422(client, query):
    response = client.get(f'/v2/suggestion{query}')

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
