# ruff: noqa: PLR2004, PLR0913, PLR0917
"""Faceta hierárquica `territory_city`: território (código SEI) com os
municípios (código IBGE) como filhos; o `facet_limit` vale por nível."""

from http import HTTPStatus

import pytest

SERRINHA = ('Serrinha', '2930501', 4, 'SISAL')
CONCEICAO = ('Conceição do Coité', '2908408', 4, 'SISAL')
VALENTE = ('Valente', '2933059', 4, 'SISAL')
CACHOEIRA = ('Cachoeira', '2904902', 21, 'RECÔNCAVO')
SALVADOR = ('Salvador', '2927408', 26, 'METROPOLITANA DE SALVADOR')


def _facet(response, name='territory_city'):
    assert response.status_code == HTTPStatus.OK, response.text
    return response.json()['facets'][name]


def _tree(facet):
    return [
        (
            t['value'],
            t['label'],
            t['count'],
            t['selected'],
            [(c['value'], c['count'], c['selected']) for c in t['children']],
        )
        for t in facet['items']
    ]


@pytest.fixture
def link(researcher_factory, researcher_institution_factory):
    async def _link(name, *cities):
        researcher = await researcher_factory(name=name)
        for city in cities:
            await researcher_institution_factory(
                researcher_id=researcher.id, city_id=city.id
            )
        return researcher

    return _link


@pytest.mark.asyncio
async def test_territory_city_shape_counts_and_no_territory_group(
    client, geo_city, link, refresh_mvs
):
    serrinha = await geo_city(*SERRINHA)
    cachoeira = await geo_city(*CACHOEIRA)
    sao_paulo = await geo_city('São Paulo', '3550308', None, uf='SP')
    await link('A', serrinha)
    # Dois vínculos, dois territórios: conta uma vez em cada território
    await link('B', serrinha, cachoeira)
    await link('C', sao_paulo)
    await refresh_mvs()

    facet = _facet(client.get('/v2/researcher?facets=territory_city'))

    assert facet['param'] == ['identity_territory', 'city_code']
    assert facet['total'] == 3
    assert facet['covered'] == 3
    assert _tree(facet) == [
        ('4', 'SISAL', 2, False, [('2930501', 2, False)]),
        ('21', 'RECÔNCAVO', 1, False, [('2904902', 1, False)]),
        (None, 'Sem território', 1, False, [('3550308', 1, False)]),
    ]
    sisal = facet['items'][0]
    assert sisal['code'] == 4
    assert sisal['children'][0]['code'] == 2930501
    assert sisal['children'][0]['label'] == 'Serrinha'
    assert 'children' not in sisal['children'][0]


@pytest.mark.asyncio
async def test_territory_count_is_distinct_not_sum_of_children(
    client, geo_city, link, refresh_mvs
):
    serrinha = await geo_city(*SERRINHA)
    valente = await geo_city(*VALENTE)
    await link('A', serrinha, valente)
    await refresh_mvs()

    facet = _facet(client.get('/v2/researcher?facets=territory_city'))

    assert _tree(facet) == [
        (
            '4',
            'SISAL',
            1,
            False,
            [('2930501', 1, False), ('2933059', 1, False)],
        )
    ]
    assert facet['covered'] == 1


@pytest.mark.asyncio
async def test_facet_limit_applies_per_level(
    client, geo_city, link, refresh_mvs
):
    serrinha = await geo_city(*SERRINHA)
    conceicao = await geo_city(*CONCEICAO)
    valente = await geo_city(*VALENTE)
    cachoeira = await geo_city(*CACHOEIRA)
    salvador = await geo_city(*SALVADOR)
    await link('A', serrinha)
    await link('B', serrinha)
    await link('C', conceicao)
    await link('D', valente)
    await link('E', cachoeira)
    await link('F', salvador)
    await refresh_mvs()

    facet = _facet(
        client.get('/v2/researcher?facets=territory_city&facet_limit=2')
    )

    assert facet['total'] == 3
    assert [t['value'] for t in facet['items']] == ['4', '26']
    sisal = facet['items'][0]
    assert sisal['count'] == 4
    assert [c['value'] for c in sisal['children']] == ['2930501', '2908408']


@pytest.mark.asyncio
async def test_filters_are_disjunctive_and_selected_values_are_kept(
    client, geo_city, link, refresh_mvs
):
    serrinha = await geo_city(*SERRINHA)
    cachoeira = await geo_city(*CACHOEIRA)
    await geo_city(*SALVADOR)
    await link('Em Serrinha', serrinha)
    await link('Em Cachoeira', cachoeira)
    await refresh_mvs()

    response = client.get(
        '/v2/researcher?identity_territory=4&city_code=2927408'
        '&facets=territory_city,identity_territory'
    )

    # Território 4 E município Salvador: nenhum pesquisador nos dois
    assert response.json()['data'] == []
    # A faceta ignora os filtros de território e cidade
    assert _tree(_facet(response)) == [
        ('21', 'RECÔNCAVO', 1, False, [('2904902', 1, False)]),
        ('4', 'SISAL', 1, True, [('2930501', 1, False)]),
        (
            '26',
            'METROPOLITANA DE SALVADOR',
            0,
            False,
            [('2927408', 0, True)],
        ),
    ]


@pytest.mark.asyncio
async def test_city_code_filter_and_city_facet_code(
    client, geo_city, link, refresh_mvs
):
    serrinha = await geo_city(*SERRINHA, city_name='Serrinha  Ba')
    cachoeira = await geo_city(*CACHOEIRA)
    await link('Em Serrinha', serrinha)
    await link('Em Cachoeira', cachoeira)
    await refresh_mvs()

    response = client.get('/v2/researcher?city_code=2930501&facets=city')

    assert [r['name'] for r in response.json()['data']] == ['Em Serrinha']
    codes = {i['label']: i['code'] for i in _facet(response, 'city')['items']}
    assert codes == {'Serrinha  Ba': 2930501, 'Cachoeira': 2904902}


@pytest.mark.asyncio
async def test_production_territory_city_counts_productions(
    client, geo_city, link, article_factory, refresh_mvs
):
    serrinha = await geo_city(*SERRINHA)
    author = await link('Autora', serrinha)
    await article_factory(author, 'Artigo Um')
    await article_factory(author, 'Artigo Dois')
    await refresh_mvs()

    facet = _facet(client.get('/v2/production/article?facets=territory_city'))

    assert _tree(facet) == [('4', 'SISAL', 2, False, [('2930501', 2, False)])]
    assert facet['covered'] == 2


@pytest.mark.asyncio
async def test_graduate_program_territory_from_headquarters(
    client, geo_city, graduate_program_factory
):
    await geo_city(*SALVADOR)
    await geo_city(*CACHOEIRA)
    await graduate_program_factory(
        name='Programa Salvador', city='Salvador', state='BA'
    )
    await graduate_program_factory(
        name='Programa Cachoeira', city='cachoeira ', state='BA'
    )
    await graduate_program_factory(
        name='Programa Fora', city='Recife', state='PE'
    )

    response = client.get(
        '/v2/graduate-program?identity_territory=26'
        '&facets=identity_territory,territory_city&facet_limit=27'
    )

    assert [p['name'] for p in response.json()['data']] == [
        'Programa Salvador'
    ]
    territories = _facet(response, 'identity_territory')
    assert territories['param'] == 'identity_territory'
    assert {
        (i['value'], i['count'], i['selected']) for i in territories['items']
    } == {('26', 1, True), ('21', 1, False)}
    # Programa fora da BA não tem município na referência: fica de fora
    assert territories['covered'] == 2
    # Empate na contagem: ordem alfabética do rótulo
    assert _tree(_facet(response)) == [
        (
            '26',
            'METROPOLITANA DE SALVADOR',
            1,
            True,
            [('2927408', 1, False)],
        ),
        ('21', 'RECÔNCAVO', 1, False, [('2904902', 1, False)]),
    ]

    by_city = client.get('/v2/graduate-program?city_code=2904902')
    assert [p['name'] for p in by_city.json()['data']] == [
        'Programa Cachoeira'
    ]
