from decimal import Decimal

import pytest

from simcc.data_consistency.comparison import (
    DEFAULT_LOWER_TOLERANCE,
    DEFAULT_UPPER_TOLERANCE,
    NEW_SCOPE,
    NORMAL,
    UNCHANGED,
    WARNING,
    compare_values,
)


def test_values_inside_thresholds_are_normal():
    result = compare_values(100, 96)

    assert result.status == NORMAL
    assert result.is_warning is False
    assert result.variation_percent == Decimal('-4')
    assert result.warning_reason is None


@pytest.mark.parametrize(
    ('before', 'after', 'variation', 'reason'),
    [
        (100, 95, Decimal('-5'), 'DECREASE_BELOW_TOLERANCE'),
        (100, 110, Decimal('10'), 'INCREASE_ABOVE_TOLERANCE'),
        (100, 0, Decimal('-100'), 'VALUE_REDUCED_TO_ZERO'),
    ],
)
def test_thresholds_are_inclusive(before, after, variation, reason):
    result = compare_values(before, after)

    assert result.status == WARNING
    assert result.is_warning is True
    assert result.variation_percent == variation
    assert result.warning_reason == reason


def test_zero_baseline_creates_new_scope_without_warning():
    result = compare_values(0, 25)

    assert result.status == NEW_SCOPE
    assert result.is_warning is False
    assert result.variation_percent is None


def test_both_zero_and_unchanged_positive_values_are_unchanged():
    assert compare_values(0, 0).status == UNCHANGED
    assert compare_values(25, 25).status == UNCHANGED


def test_custom_tolerances_are_preserved():
    result = compare_values(
        100,
        94,
        lower_tolerance=Decimal('7'),
        upper_tolerance=Decimal('12'),
    )

    assert result.status == NORMAL
    assert result.lower_tolerance == Decimal('7')
    assert result.upper_tolerance == Decimal('12')


@pytest.mark.parametrize(
    'kwargs',
    [
        {'before_value': -1, 'after_value': 1},
        {'before_value': 1, 'after_value': -1},
        {
            'before_value': 1,
            'after_value': 1,
            'lower_tolerance': Decimal('-1'),
        },
    ],
)
def test_invalid_values_are_rejected(kwargs):
    with pytest.raises((TypeError, ValueError)):
        compare_values(**kwargs)


def test_default_tolerances_match_the_business_rule():
    assert DEFAULT_LOWER_TOLERANCE == Decimal('5')
    assert DEFAULT_UPPER_TOLERANCE == Decimal('10')
