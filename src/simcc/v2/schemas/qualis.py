"""Qualis CAPES e JCR tipados.

O banco guarda o Qualis como texto livre: estratos (`A1`...`C`), `SQ` (sem
Qualis), `NP` (não se aplica), `None` ou vazio. A API expõe o estrato como
enum fechado e o motivo da ausência em `qualis_status`.
"""

from typing import Annotated, Any, Literal, Optional

from pydantic import BeforeValidator

QualisRank = Literal[
    'A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4', 'B5', 'C'
]
QualisStatus = Literal['not_rated', 'not_applicable']

_RANKS = frozenset(QualisRank.__args__)
_STATUS_TO_DB = {'not_rated': 'SQ', 'not_applicable': 'NP'}
_DB_TO_STATUS = {v: k for k, v in _STATUS_TO_DB.items()}


def parse_qualis(
    value: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """Valor do banco → (estrato, motivo da ausência)."""
    if value is None:
        return None, None
    cleaned = value.strip().upper()
    if cleaned in _RANKS:
        return cleaned, None
    return None, _DB_TO_STATUS.get(cleaned)


def qualis_from_db(value: str) -> Optional[str]:
    """Valor do banco → valor de filtro/faceta (estrato ou motivo)."""
    rank, status = parse_qualis(value)
    return rank or status


def qualis_to_db(value: str) -> str:
    """Valor de filtro → valor gravado no banco."""
    return _STATUS_TO_DB.get(value, value)


def _normalize_filter_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    upper = cleaned.upper()
    if upper in _RANKS:
        return upper
    if upper in _DB_TO_STATUS:
        return _DB_TO_STATUS[upper]
    return cleaned.lower()


# Filtro/faceta: estrato ou motivo da ausência; aceita `SQ` e `NP`
QualisFilterValue = Annotated[
    Literal[
        'A1',
        'A2',
        'A3',
        'A4',
        'B1',
        'B2',
        'B3',
        'B4',
        'B5',
        'C',
        'not_rated',
        'not_applicable',
    ],
    BeforeValidator(_normalize_filter_value),
]


def parse_jcr(value: Any) -> Optional[float]:
    """Fator de impacto como número; vírgula decimal aceita."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(',', '.')
    try:
        return float(text)
    except ValueError:
        return None
