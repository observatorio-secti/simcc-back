# ruff: noqa: PLR2004
from http import HTTPStatus

import pytest

from simcc.core.db.models.graduate_program import GraduateProgramResearcher


async def _researchers_in(researcher_factory, institution, n, name='Facet'):
    for i in range(n):
        await researcher_factory(
            name=f'{name} {institution.name} {i}',
            institution_id=institution.id,
        )


@pytest.mark.asyncio
async def test_institution_facet_counts_every_affiliation(
    client,
    researcher_factory,
    institution_factory,
    researcher_institution_factory,
):
    inst_a = await institution_factory(name='Facet A')
    inst_b = await institution_factory(name='Facet B')
    researcher = await researcher_factory(institution_id=inst_a.id)
    await researcher_institution_factory(
        researcher_id=researcher.id, institution_id=inst_b.id
    )
    await researcher_factory(institution_id=inst_a.id)

    facet = client.get('/v2/researcher?facets=institution').json()['facets']

    counts = {f['label']: f['count'] for f in facet['institution']['items']}
    assert counts == {'Facet A': 2, 'Facet B': 1}


@pytest.mark.asyncio
async def test_graduate_program_facet(
    client,
    session,
    researcher_factory,
    graduate_program_factory,
    refresh_mvs,
):
    gp = await graduate_program_factory(name='Programa Facet')
    researcher = await researcher_factory()
    session.add(
        GraduateProgramResearcher(
            graduate_program_id=gp.graduate_program_id,
            researcher_id=researcher.id,
        )
    )
    await session.commit()
    await refresh_mvs()

    response = client.get('/v2/researcher?facets=graduate_program')

    assert response.status_code == HTTPStatus.OK
    assert response.json()['facets']['graduate_program'] == {
        'total': 1,
        'items': [
            {
                'value': str(gp.graduate_program_id),
                'label': 'Programa Facet',
                'count': 1,
                'acronym': gp.acronym,
                'selected': False,
            }
        ],
    }


@pytest.mark.asyncio
async def test_facet_items_ordered_by_count_then_name(
    client, researcher_factory, institution_factory
):
    beta = await institution_factory(name='Beta', acronym='BT')
    alpha = await institution_factory(name='Alpha', acronym='AL')
    gamma = await institution_factory(name='Gamma', acronym=None)
    await _researchers_in(researcher_factory, beta, 1)
    await _researchers_in(researcher_factory, alpha, 1)
    await _researchers_in(researcher_factory, gamma, 2)

    facet = client.get('/v2/researcher?facets=institution').json()['facets']

    assert facet['institution'] == {
        'total': 3,
        'items': [
            {
                'value': str(gamma.id),
                'label': 'Gamma',
                'count': 2,
                'acronym': None,
                'selected': False,
            },
            {
                'value': str(alpha.id),
                'label': 'Alpha',
                'count': 1,
                'acronym': 'AL',
                'selected': False,
            },
            {
                'value': str(beta.id),
                'label': 'Beta',
                'count': 1,
                'acronym': 'BT',
                'selected': False,
            },
        ],
    }


@pytest.mark.asyncio
async def test_facet_limit_truncates_but_total_counts_all(
    client, researcher_factory, institution_factory
):
    for name in ('Um', 'Dois', 'Tres'):
        inst = await institution_factory(name=name)
        await _researchers_in(researcher_factory, inst, 1)

    facet = client.get(
        '/v2/researcher?facets=institution&facet_limit=2'
    ).json()['facets']['institution']

    assert facet['total'] == 3
    assert len(facet['items']) == 2


@pytest.mark.asyncio
async def test_facet_keeps_selected_value_beyond_limit(
    client, researcher_factory, institution_factory
):
    big = await institution_factory(name='Grande')
    small = await institution_factory(name='Pequena')
    await _researchers_in(researcher_factory, big, 3)
    await _researchers_in(researcher_factory, small, 1)

    facet = client.get(
        f'/v2/researcher?facets=institution&facet_limit=1'
        f'&institution_id={small.id}'
    ).json()['facets']['institution']

    assert facet['total'] == 2
    assert [
        (i['label'], i['count'], i['selected']) for i in facet['items']
    ] == [
        ('Grande', 3, False),
        ('Pequena', 1, True),
    ]


@pytest.mark.asyncio
async def test_facet_keeps_selected_value_with_zero_count(
    client, researcher_factory, institution_factory
):
    with_match = await institution_factory(name='Com Dengue')
    without_match = await institution_factory(name='Sem Dengue')
    await researcher_factory(
        name='Dengue Pesquisador', institution_id=with_match.id
    )
    await researcher_factory(
        name='Outro Tema', institution_id=without_match.id
    )
    empty = await institution_factory(name='Vazia')

    facet = client.get(
        f'/v2/researcher?q=Dengue&facets=institution&institution_id={empty.id}'
    ).json()['facets']['institution']

    # `Vazia` não tem pesquisadores: aparece com 0, mas não entra no total
    assert facet['total'] == 1
    assert [
        (i['label'], i['count'], i['selected']) for i in facet['items']
    ] == [
        ('Com Dengue', 1, False),
        ('Vazia', 0, True),
    ]


@pytest.mark.asyncio
async def test_facet_respects_other_filters(  # noqa: PLR0913, PLR0917
    client,
    session,
    researcher_factory,
    institution_factory,
    graduate_program_factory,
    refresh_mvs,
):
    inst = await institution_factory(name='Instituto Programa')
    gp_in = await graduate_program_factory(name='Programa Dentro')
    gp_out = await graduate_program_factory(name='Programa Fora')
    inside = await researcher_factory(institution_id=inst.id)
    outside = await researcher_factory()
    session.add_all([
        GraduateProgramResearcher(
            graduate_program_id=gp_in.graduate_program_id,
            researcher_id=inside.id,
        ),
        GraduateProgramResearcher(
            graduate_program_id=gp_out.graduate_program_id,
            researcher_id=outside.id,
        ),
    ])
    await session.commit()
    await refresh_mvs()

    facet = client.get(
        f'/v2/researcher?facets=graduate_program&institution_id={inst.id}'
    ).json()['facets']['graduate_program']

    assert [i['label'] for i in facet['items']] == ['Programa Dentro']


@pytest.mark.asyncio
async def test_year_facet_shape(client, researcher_factory):
    await researcher_factory()

    facet = client.get('/v2/researcher?facets=year').json()['facets']['year']

    assert facet == {'total': 0, 'items': []}


@pytest.mark.asyncio
@pytest.mark.parametrize('value', [0, 101])
async def test_facet_limit_validation(client, value):
    response = client.get(
        f'/v2/researcher?facets=institution&facet_limit={value}'
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
