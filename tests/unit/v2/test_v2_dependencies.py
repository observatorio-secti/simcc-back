from uuid import uuid4

import pytest

from simcc.v2.dependencies import (
    common_filter_params,
    pagination_params,
    researcher_filter_params,
    researcher_query_params,
    sort_params,
)

YEAR_2020 = 2020
YEAR_2024 = 2024
CUSTOM_PAGE = 3
CUSTOM_PER_PAGE = 50


@pytest.mark.unit
def test_pagination_params_default():
    params = pagination_params()
    assert params == {'page': 1, 'per_page': 20}


@pytest.mark.unit
def test_pagination_params_custom():
    params = pagination_params(page=CUSTOM_PAGE, per_page=CUSTOM_PER_PAGE)
    assert params == {'page': CUSTOM_PAGE, 'per_page': CUSTOM_PER_PAGE}


@pytest.mark.unit
def test_sort_params_default():
    params = sort_params()
    assert params == {'by': 'name', 'order': 'asc'}


@pytest.mark.unit
def test_sort_params_custom():
    params = sort_params(sort_by='created_at', sort_order='desc')
    assert params == {'by': 'created_at', 'order': 'desc'}


@pytest.mark.unit
def test_common_filter_params_with_q():
    params = common_filter_params(q=' Inteligencia Artificial ')
    assert params['q'] == 'Inteligencia Artificial'
    assert params['year_start'] is None
    assert params['year_end'] is None
    assert params['institution_id'] is None


@pytest.mark.unit
def test_common_filter_params_with_query_alias():
    params = common_filter_params(query=' Redes Neurais ')
    assert params['q'] == 'Redes Neurais'


@pytest.mark.unit
def test_common_filter_params_prefers_q_over_query():
    params = common_filter_params(q='Termo Principal', query='Termo Alias')
    assert params['q'] == 'Termo Principal'


@pytest.mark.unit
def test_common_filter_params_empty_whitespace():
    params = common_filter_params(q='   ')
    assert params['q'] is None


@pytest.mark.unit
def test_researcher_filter_params():
    inst_id = uuid4()
    gp_id = uuid4()
    common = common_filter_params(
        q='Pesquisa',
        year_start=YEAR_2020,
        year_end=YEAR_2024,
        institution_id=inst_id,
    )
    res_filters = researcher_filter_params(
        common=common,
        graduate_program_id=gp_id,
    )

    assert res_filters['q'] == 'Pesquisa'
    assert res_filters['year_start'] == YEAR_2020
    assert res_filters['year_end'] == YEAR_2024
    assert res_filters['institution_id'] == inst_id
    assert res_filters['graduate_program_id'] == gp_id


@pytest.mark.unit
def test_researcher_query_params_composition():
    filters = {'q': 'IA', 'graduate_program_id': None}
    pagination = {'page': 1, 'per_page': 20}
    sort = {'by': 'name', 'order': 'asc'}

    result = researcher_query_params(
        filters=filters,
        pagination=pagination,
        sort=sort,
    )
    assert result['filters'] == filters
    assert result['pagination'] == pagination
    assert result['sort'] == sort
