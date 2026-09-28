# ruff: noqa: PLC2701, PLR2004
import uuid

import pytest

from simcc.v2.repositories.researcher_filters import (
    _by_cities,
    _by_classification,
    _by_graduate_programs,
    _by_graduation,
    _by_identity_territories,
    _by_institutions,
    _by_search_query,
    _by_source_type,
    _by_year_range,
    build_researcher_conditions,
    without_fields,
)
from simcc.v2.schemas.filters import ResearcherFilter


def test_by_search_query_returns_condition():
    filter_obj = ResearcherFilter(q='Carlos')
    cond = _by_search_query(filter_obj)
    assert cond is not None


@pytest.mark.parametrize('empty_q', [None, '', '   '])
def test_by_search_query_empty_returns_none(empty_q):
    filter_obj = ResearcherFilter(q=empty_q)
    assert _by_search_query(filter_obj) is None


def test_by_institutions_returns_condition():
    inst_id = uuid.uuid4()
    filter_obj = ResearcherFilter(institution_id=[inst_id])
    cond = _by_institutions(filter_obj)
    assert cond is not None


def test_by_institutions_none_returns_none():
    filter_obj = ResearcherFilter(institution_id=[])
    assert _by_institutions(filter_obj) is None


def test_by_graduate_programs_returns_condition():
    prog_id = uuid.uuid4()
    filter_obj = ResearcherFilter(graduate_program_id=[prog_id])
    cond = _by_graduate_programs(filter_obj)
    assert cond is not None


def test_by_graduate_programs_none_returns_none():
    filter_obj = ResearcherFilter(graduate_program_id=[])
    assert _by_graduate_programs(filter_obj) is None


@pytest.mark.parametrize(
    ('year_start', 'year_end'),
    [
        (2020, None),
        (None, 2024),
        (2020, 2024),
    ],
)
def test_by_year_range_returns_condition(year_start, year_end):
    filter_obj = ResearcherFilter(year_start=year_start, year_end=year_end)
    cond = _by_year_range(filter_obj)
    assert cond is not None


def test_by_year_range_both_none_returns_none():
    filter_obj = ResearcherFilter(year_start=None, year_end=None)
    assert _by_year_range(filter_obj) is None


def test_by_year_range_with_q_returns_none_in_builder():
    # When q is provided, year range is handled inside the search query EXISTS
    filter_obj = ResearcherFilter(q='Inteligência', year_start=2020)
    assert _by_year_range(filter_obj) is None


@pytest.mark.parametrize(
    ('kwargs', 'expected_count'),
    [
        ({}, 0),
        ({'q': 'Ana'}, 1),
        ({'institution_id': [uuid.uuid4()]}, 1),
        ({'graduate_program_id': [uuid.uuid4()]}, 1),
        ({'year_start': 2020}, 1),
        ({'year_start': 2020, 'year_end': 2023}, 1),
        (
            {
                'q': 'Ana',
                'institution_id': [uuid.uuid4()],
            },
            2,
        ),
        (
            {
                'q': 'Ana',
                'institution_id': [uuid.uuid4()],
                'graduate_program_id': [uuid.uuid4()],
                'year_start': 2020,
                'year_end': 2023,
            },
            3,  # q handles years, institution_id, graduate_program_id
        ),
    ],
)
def test_build_researcher_conditions_combinations(kwargs, expected_count):
    filter_obj = ResearcherFilter(**kwargs)
    conditions = build_researcher_conditions(filter_obj)
    assert len(conditions) == expected_count


def test_build_researcher_conditions_disjunctive_exclusion():
    inst_id = uuid.uuid4()
    filter_obj = ResearcherFilter(
        q='Maria',
        institution_id=[inst_id],
    )
    # Exclude institution_id for disjunctive faceting
    conditions = build_researcher_conditions(
        filter_obj, exclude=frozenset({'institution_id'})
    )
    assert len(conditions) == 1


@pytest.mark.parametrize(
    ('builder', 'kwargs'),
    [
        (_by_cities, {'city_id': [uuid.uuid4()]}),
        (_by_identity_territories, {'identity_territory': ['Sisal']}),
        (_by_graduation, {'graduation': ['Doutorado']}),
        (_by_classification, {'classification': ['A+']}),
        (_by_source_type, {'source_type': ['ARTICLE']}),
    ],
)
def test_new_builders_only_apply_when_set(builder, kwargs):
    assert builder(ResearcherFilter()) is None
    assert builder(ResearcherFilter(**kwargs)) is not None


def test_source_type_is_handled_by_search_query_when_q_present():
    filter_obj = ResearcherFilter(q='dengue', source_type=['ARTICLE'])
    assert _by_source_type(filter_obj) is None
    assert len(build_researcher_conditions(filter_obj)) == 1


def test_year_range_is_handled_by_source_type_without_q():
    filter_obj = ResearcherFilter(source_type=['BOOK'], year_start=2020)
    assert _by_year_range(filter_obj) is None
    assert len(build_researcher_conditions(filter_obj)) == 1


def test_classification_rejects_unknown_value():
    with pytest.raises(ValueError, match='classification'):
        ResearcherFilter(classification=['Z'])


def test_without_fields_resets_to_defaults():
    filter_obj = ResearcherFilter(
        q='dengue', year_start=2020, year_end=2022, city_id=[uuid.uuid4()]
    )
    cleared = without_fields(filter_obj, frozenset({'year_start', 'city_id'}))
    assert cleared.year_start is None
    assert cleared.city_id == []
    assert cleared.year_end == 2022
    assert filter_obj.year_start == 2020  # original intacto
