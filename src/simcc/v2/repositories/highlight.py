"""Trechos destacados: texto puro + intervalos, sem HTML nem marcadores.

O `ts_headline` do Postgres delimita os termos com caracteres de uso privado
do Unicode (que não aparecem em texto real); aqui eles são removidos e
viram intervalos `[início, fim)` em unidades UTF-16 — as mesmas de
`String.prototype.slice` no JavaScript.
"""

START = ''
STOP = ''

HEADLINE_OPTIONS = f'StartSel={START}, StopSel={STOP}'
HEADLINE_ALL_OPTIONS = f'{HEADLINE_OPTIONS}, HighlightAll=TRUE'
HEADLINE_EXCERPT_OPTIONS = f'{HEADLINE_OPTIONS}, MaxWords=35, MinWords=15'


def _utf16_len(text: str) -> int:
    return len(text.encode('utf-16-le')) // 2


def has_highlight(marked: str | None) -> bool:
    return bool(marked) and START in marked


def parse_highlight(marked: str | None) -> tuple[str, list[list[int]]]:
    """Separa o texto dos intervalos destacados.

    >>> parse_highlight('a \\ue000b\\ue001 c')
    ('a b c', [[2, 3]])
    """
    if not marked:
        return '', []
    plain: list[str] = []
    ranges: list[list[int]] = []
    position = 0
    start = None
    for char in marked:
        if char == START:
            start = position
        elif char == STOP:
            if start is not None and position > start:
                ranges.append([start, position])
            start = None
        else:
            plain.append(char)
            position += _utf16_len(char)
    return ''.join(plain), _merge(ranges)


def _merge(ranges: list[list[int]]) -> list[list[int]]:
    """Une intervalos adjacentes (termos seguidos viram um só trecho)."""
    merged: list[list[int]] = []
    for begin, end in ranges:
        if merged and begin <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([begin, end])
    return merged
