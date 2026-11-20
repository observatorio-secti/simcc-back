"""Conversão do `ts_headline` marcado em texto puro + intervalos UTF-16."""

from simcc.v2.repositories.highlight import (
    START,
    STOP,
    has_highlight,
    parse_highlight,
)
from simcc.v2.schemas.production import ArticleMatch


def _utf16_slice(text: str, begin: int, end: int) -> str:
    raw = text.encode('utf-16-le')
    return raw[begin * 2 : end * 2].decode('utf-16-le')


def test_plain_text_and_ranges():
    text, ranges = parse_highlight(f'Saúde {START}pública{STOP} no SUS')

    assert text == 'Saúde pública no SUS'
    assert ranges == [[6, 13]]
    assert _utf16_slice(text, *ranges[0]) == 'pública'


def test_ranges_count_utf16_units_for_emoji():
    # O emoji ocupa 2 unidades UTF-16 (como no JavaScript)
    text, ranges = parse_highlight(f'🌱 {START}solo{STOP}')

    assert text == '🌱 solo'
    assert ranges == [[3, 7]]
    assert _utf16_slice(text, *ranges[0]) == 'solo'


def test_adjacent_ranges_are_merged_and_empty_ignored():
    marked = f'{START}a{STOP}{START}b{STOP} {START}{STOP}c'

    assert parse_highlight(marked) == ('ab c', [[0, 2]])


def test_has_highlight_and_empty_input():
    assert has_highlight(f'x {START}y{STOP}')
    assert not has_highlight('sem destaque')
    assert parse_highlight(None) == ('', [])


def test_article_match_from_marked():
    match = ArticleMatch.from_marked('title', f'Redes {START}neurais{STOP}')

    assert match.snippet == 'Redes neurais'
    assert match.highlights == [(6, 13)]
