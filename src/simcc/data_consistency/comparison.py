from dataclasses import dataclass
from decimal import Decimal
from typing import Final

NORMAL: Final = 'NORMAL'
WARNING: Final = 'WARNING'
NEW_SCOPE: Final = 'NEW_SCOPE'
UNCHANGED: Final = 'UNCHANGED'

DEFAULT_LOWER_TOLERANCE = Decimal('5')
DEFAULT_UPPER_TOLERANCE = Decimal('10')


@dataclass(frozen=True)
class ComparisonResult:
    before_value: int
    after_value: int
    absolute_difference: int
    variation_percent: Decimal | None
    lower_tolerance: Decimal
    upper_tolerance: Decimal
    status: str
    is_warning: bool
    warning_reason: str | None = None


def compare_values(
    before_value: int,
    after_value: int,
    *,
    lower_tolerance: Decimal = DEFAULT_LOWER_TOLERANCE,
    upper_tolerance: Decimal = DEFAULT_UPPER_TOLERANCE,
) -> ComparisonResult:
    """Compare two non-negative metric values using inclusive thresholds."""
    _validate_value('before_value', before_value)
    _validate_value('after_value', after_value)
    _validate_tolerance('lower_tolerance', lower_tolerance)
    _validate_tolerance('upper_tolerance', upper_tolerance)

    difference = after_value - before_value
    if before_value == 0:
        if after_value == 0:
            return _result(
                (before_value, after_value, difference),
                Decimal('0'),
                (lower_tolerance, upper_tolerance),
                UNCHANGED,
            )
        return _result(
            (before_value, after_value, difference),
            None,
            (lower_tolerance, upper_tolerance),
            NEW_SCOPE,
        )

    variation = (
        Decimal(difference) / Decimal(before_value) * Decimal('100')
    )
    if variation <= -lower_tolerance:
        reason = (
            'VALUE_REDUCED_TO_ZERO'
            if after_value == 0
            else 'DECREASE_BELOW_TOLERANCE'
        )
        return _result(
            (before_value, after_value, difference),
            variation,
            (lower_tolerance, upper_tolerance),
            WARNING,
            reason,
        )
    if variation >= upper_tolerance:
        return _result(
            (before_value, after_value, difference),
            variation,
            (lower_tolerance, upper_tolerance),
            WARNING,
            'INCREASE_ABOVE_TOLERANCE',
        )

    status = UNCHANGED if difference == 0 else NORMAL
    return _result(
        (before_value, after_value, difference),
        variation,
        (lower_tolerance, upper_tolerance),
        status,
    )


def _result(
    values: tuple[int, int, int],
    variation_percent: Decimal | None,
    tolerances: tuple[Decimal, Decimal],
    status: str,
    warning_reason: str | None = None,
) -> ComparisonResult:
    before_value, after_value, difference = values
    lower_tolerance, upper_tolerance = tolerances
    return ComparisonResult(
        before_value=before_value,
        after_value=after_value,
        absolute_difference=difference,
        variation_percent=variation_percent,
        lower_tolerance=lower_tolerance,
        upper_tolerance=upper_tolerance,
        status=status,
        is_warning=status == WARNING,
        warning_reason=warning_reason,
    )


def _validate_value(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f'{name} must be an integer')
    if value < 0:
        raise ValueError(f'{name} cannot be negative')


def _validate_tolerance(name: str, value: Decimal) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f'{name} must be a Decimal')
    if value < 0:
        raise ValueError(f'{name} cannot be negative')
