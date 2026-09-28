from uuid import uuid4
from simcc.v1.queries.metrics_query import GraduateProgramProductionQuery
from simcc.v1.schemas import DefaultFilters


def test_graduate_program_production_query_excludes_externa_with_program_id():
    query = GraduateProgramProductionQuery(session=None)
    gp_id = uuid4()
    filters = DefaultFilters(graduate_program_id=gp_id, year=2020)
    query.apply_filters(filters)
    sql = query.build_sql()

    # Verifica se a exclusão da instituição EXTERNA está presente
    assert "COALESCE(i.acronym, '') <> 'EXTERNA'" in sql
    assert "i.acronym = 'EXTERNA'" in sql  # Subquery para o programa de pós
    assert query.params['graduate_program_id'] == str(gp_id)
    assert query.params['year'] == 2020
    assert "COALESCE(i.acronym, '') <> 'EXTERNA'" in query._researcher_sql


def test_graduate_program_production_query_excludes_externa_general():
    query = GraduateProgramProductionQuery(session=None)
    filters = DefaultFilters(year=2020)
    query.apply_filters(filters)
    sql = query.build_sql()

    # Verifica se a exclusão da instituição EXTERNA está presente no cálculo geral
    assert "COALESCE(i.acronym, '') <> 'EXTERNA'" in sql
    assert "LEFT JOIN institution i ON r.institution_id = i.id" in sql
    assert query.params['year'] == 2020
    assert "COALESCE(i.acronym, '') <> 'EXTERNA'" in query._researcher_sql
