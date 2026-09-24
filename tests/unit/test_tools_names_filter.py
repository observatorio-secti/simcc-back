from simcc.v1.queries.researcher_query import ResearcherSearchQuery
from simcc.v1.queries.term_query import OriginalWordsQuery
from simcc.v1.repositories.tools import names_filter


def test_names_filter_multi_token_matches():
    sql, params = names_filter('r.name', 'Eduardo Jorge')
    assert 'unaccent(LOWER(r.name)) LIKE :name_tok_0' in sql
    assert 'unaccent(LOWER(r.name)) LIKE :name_tok_1' in sql
    assert params['name_tok_0'] == '%eduardo%'
    assert params['name_tok_1'] == '%jorge%'


def test_names_filter_accents_and_special_chars():
    sql, params = names_filter('ur.full_name', '(Cláudio ; Santos)')
    assert 'unaccent(LOWER(ur.full_name)) LIKE :name_tok_0' in sql
    assert 'unaccent(LOWER(ur.full_name)) LIKE :name_tok_1' in sql
    assert params['name_tok_0'] == '%claudio%'
    assert params['name_tok_1'] == '%santos%'


def test_names_filter_empty():
    sql, params = names_filter('r.name', '   ')
    assert sql == ''
    assert params == {}


def test_original_words_query_name_multi_token():
    query = OriginalWordsQuery(
        session=None, initials='Eduardo Jorge', type_='NAME'
    )
    sql = query.build_sql()
    assert 'unaccent(LOWER(name)) LIKE :init_tok_0' in sql
    assert 'unaccent(LOWER(name)) LIKE :init_tok_1' in sql
    assert query.params['init_tok_0'] == '%eduardo%'
    assert query.params['init_tok_1'] == '%jorge%'


def test_researcher_search_query_name_integration():
    class DummySession:
        pass

    query = ResearcherSearchQuery(session=DummySession(), name='Eduardo Jorge')
    sql = query.build_sql()
    assert 'unaccent(LOWER(r.name)) LIKE :name_tok_0' in sql
    assert 'unaccent(LOWER(r.name)) LIKE :name_tok_1' in sql
    assert query.params['name_tok_0'] == '%eduardo%'
    assert query.params['name_tok_1'] == '%jorge%'
