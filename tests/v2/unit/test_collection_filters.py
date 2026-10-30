from uuid import uuid4
import pytest
from sqlalchemy import Table, MetaData, Column, Integer
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID

from simcc.v1.schemas import DefaultFilters
from simcc.v1.queries.researcher_query import (
    ResearcherSearchQuery,
    ResearcherFilterQuery,
    OutstandingResearchersQuery,
)
from simcc.v1.queries.production_query import BaseProductionQuery
from simcc.v1.queries.metrics_query import (
    BaseMetricsQuery,
    GraduateProgramProductionQuery,
    LattesUpdateMetricsQuery,
)
from simcc.v2.schemas.filters import ResearcherFilter
from simcc.v2.schemas.production import ProductionBaseFilter, ArticleFilter
from simcc.v2.repositories.researcher_filters import (
    _by_collections,
    build_researcher_conditions,
)
from simcc.v2.repositories.production_repo import build_production_conditions


@pytest.fixture(scope='session', autouse=True)
def setup_database():
    """Sobrescreve fixture global para testes sem banco/docker."""
    return


class DummySession:
    pass


# ---------------------------------------------------------------------------
# V2 Tests
# ---------------------------------------------------------------------------

def test_v2_researcher_filter_default_collection():
    rf = ResearcherFilter()
    assert rf.collection == ['simcc']


def test_v2_researcher_filter_collection_string_normalization():
    rf1 = ResearcherFilter(collection='simcc,fomento')
    assert rf1.collection == ['simcc', 'fomento']

    rf2 = ResearcherFilter(collection=['simcc; fomento'])
    assert rf2.collection == ['simcc', 'fomento']


def test_v2_by_collections_default():
    rf = ResearcherFilter()
    cond = _by_collections(rf)
    assert cond is not None
    compiled = str(cond)
    assert 'collection_slugs' in compiled


def test_v2_by_collections_all_and_wildcard():
    assert _by_collections(ResearcherFilter(collection=['all'])) is None
    assert _by_collections(ResearcherFilter(collection=['*'])) is None
    assert _by_collections(ResearcherFilter(collection='all')) is None
    assert _by_collections(ResearcherFilter(collection='*')) is None


def test_v2_production_filter_default_collection():
    pf = ProductionBaseFilter()
    assert pf.collection == ['simcc']

    af = ArticleFilter()
    assert af.collection == ['simcc']


from simcc.v2.repositories.search_tables import mv_canonical_articles


def test_v2_build_production_conditions_with_collection():
    tbl = mv_canonical_articles

    # 1. Default: collection=['simcc'] gera condição com subquery
    pf_default = ProductionBaseFilter()
    conds = build_production_conditions(tbl, pf_default)
    assert len(conds) == 1
    compiled = str(conds[0])
    assert 'researcher_ids' in compiled
    assert 'collection_slugs' in compiled

    # 2. 'all' ou '*' não deve gerar condição de coleção
    pf_all = ProductionBaseFilter(collection=['all'])
    conds_all = build_production_conditions(tbl, pf_all)
    assert len(conds_all) == 0

    pf_star = ProductionBaseFilter(collection=['*'])
    conds_star = build_production_conditions(tbl, pf_star)
    assert len(conds_star) == 0


# ---------------------------------------------------------------------------
# V1 Tests
# ---------------------------------------------------------------------------

def test_v1_default_filters_has_collection():
    df = DefaultFilters()
    assert df.collection == 'simcc'


def test_v1_researcher_search_query_collection_filter():
    session = DummySession()
    q = ResearcherSearchQuery(session)
    assert 'collection' in q.SUPPORTED_FILTERS

    # Default 'simcc'
    q.apply_filters(DefaultFilters())
    sql = q.build_sql()
    assert 'researcher_collection' in sql
    assert 'c.slug = ANY(:collections)' in sql
    assert q.params['collections'] == ['simcc']
    assert 'r.status IS True' not in sql
    assert 'r.institution_id' not in sql


def test_v1_researcher_search_query_collection_all():
    session = DummySession()
    q = ResearcherSearchQuery(session)
    q.apply_filters(DefaultFilters(collection='all'))
    sql = q.build_sql()
    assert 'researcher_collection' not in sql
    assert 'collections' not in q.params


def test_v1_researcher_filter_query_no_status_no_institution_id():
    session = DummySession()
    q = ResearcherFilterQuery(session, filters=DefaultFilters())
    sql = q.build_sql()
    assert 'r.status IS True' not in sql
    assert 'mr.institution_id' not in sql
    assert 'r.institution_id' not in sql
    assert 'researcher_collection' in sql


def test_v1_outstanding_researchers_query_no_status():
    session = DummySession()
    q = OutstandingResearchersQuery(session)
    sql = q.build_sql()
    assert 'r.status IS True' not in sql
    assert 'i.id = r.institution_id' not in sql
    assert 'researcher_institution ri' in sql


def test_v1_base_production_query_collection_and_no_institution_id():
    session = DummySession()
    q = BaseProductionQuery(session, table_alias='bp', year_col='year_')
    assert 'collection' in q.SUPPORTED_FILTERS

    q.apply_filters(DefaultFilters(institution_id=str(uuid4()), collection='simcc'))
    components = q._get_base_sql_components()
    filters_sql = components['filters']
    assert 'researcher_collection' in filters_sql
    assert 'researcher_institution ri' in filters_sql
    assert 'i.id = r.institution_id' not in filters_sql


def test_v1_metrics_query_collection_and_no_status():
    session = DummySession()
    q = BaseMetricsQuery(session)
    assert 'collection' in q.SUPPORTED_FILTERS

    q.apply_filters(DefaultFilters(institution_id=str(uuid4()), collection='simcc'))
    filters_sql = ' '.join(q.filters_sql)
    assert 'researcher_collection' in filters_sql
    assert 'researcher_institution ri' in filters_sql
    assert 'r.institution_id = :institution_id' not in filters_sql


def test_v1_graduate_program_ind_prod_metrics_no_status():
    session = DummySession()
    q = GraduateProgramProductionQuery(session)
    sql = q.build_sql()
    assert 'r.status = TRUE' not in sql
    assert 'r.institution_id = i.id' not in sql
    assert 'researcher_institution ri' in sql


def test_v1_lattes_update_metrics_no_status():
    session = DummySession()
    q = LattesUpdateMetricsQuery(session)
    sql = q.build_sql()
    assert 'r.status IS True' not in sql
