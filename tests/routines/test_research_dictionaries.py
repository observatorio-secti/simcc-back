# ruff: noqa: PLR2004
import pytest

from scripts.routines.research_dictionaries import (
    build_dictionary,
    extract_terms,
    find_nested,
    get_stopwords,
)

pytestmark = pytest.mark.unit


@pytest.fixture(scope='module')
def stopwords():
    return get_stopwords()


def test_extract_terms_keeps_inner_stopwords_only(stopwords):
    terms = extract_terms('Qualidade de vida dos idosos', stopwords)

    assert 'qualidade de vida' in terms
    assert 'qualidade de vida dos idosos' not in terms  # 5 tokens
    assert 'vida dos idosos' in terms
    assert 'qualidade de' not in terms
    assert 'de vida' not in terms
    assert 'de' not in terms


def test_extract_terms_does_not_cross_punctuation(stopwords):
    terms = extract_terms(
        'Redes neurais: aplicação (machine learning) - estudo', stopwords
    )

    assert {'redes neurais', 'machine learning', 'estudo'} <= terms
    assert 'neurais aplicação' not in terms
    assert 'aplicação machine' not in terms
    assert 'learning estudo' not in terms


def test_extract_terms_splits_hyphen_and_breaks_on_numbers(stopwords):
    terms = extract_terms('Pós-graduação e COVID-19 pandemia', stopwords)

    assert 'pós graduação' in terms
    assert 'covid' in terms
    assert 'covid pandemia' not in terms
    assert not any('19' in term for term in terms)


def test_extract_terms_unescapes_html_entities(stopwords):
    terms = extract_terms('O &quot;saber&quot; docente', stopwords)

    assert 'saber' in terms
    assert 'quot' not in terms


def test_extract_terms_counts_each_term_once_per_text(stopwords):
    terms = extract_terms('saúde pública, saúde pública', stopwords)

    assert terms == {'saúde', 'pública', 'saúde pública'}


def test_find_nested_drops_fragment_of_longer_term(stopwords):
    frequent = {
        'programa de pos': 100,
        'programa de pos graduacao': 99,
        'pos graduacao': 300,
    }

    assert find_nested(frequent, stopwords) == {'programa de pos'}


def test_build_dictionary_merges_accent_variants_and_filters(stopwords):
    contents = (
        ['Análise de redes neurais'] * 4
        + ['Analise de redes neurais'] * 2
        + ['Tema raro']
    )

    dictionary = dict(build_dictionary(contents, stopwords))

    assert dictionary['análise de redes neurais'] == 6
    assert dictionary['análise'] == 6
    assert 'analise' not in dictionary
    # fragmentos sempre contidos no termo maior
    assert 'redes neurais' not in dictionary
    assert 'análise de redes' not in dictionary
    # abaixo da frequência mínima
    assert 'tema raro' not in dictionary
