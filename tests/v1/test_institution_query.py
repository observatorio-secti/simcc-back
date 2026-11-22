from uuid import uuid4

from simcc.v1.queries.institution_query import InstitutionQuery


def test_institution_query_with_id_has_no_semicolon_before_filter():
    inst_id = uuid4()
    query = InstitutionQuery(session=None, institution_id=inst_id)
    sql = query.build_sql()

    assert query.params['institution_id'] == inst_id
    assert 'AND i.id = :institution_id' in sql

    where_clause = sql.split('WHERE i.acronym IS NOT NULL', maxsplit=1)[1]
    before_filter = where_clause.split(
        'AND i.id = :institution_id', maxsplit=1
    )[0]
    assert ';' not in before_filter


def test_institution_query_without_id_has_no_double_semicolon():
    query = InstitutionQuery(session=None)
    sql = query.build_sql()

    assert 'AND i.id = :institution_id' not in sql
    assert sql.count(';') <= 1
