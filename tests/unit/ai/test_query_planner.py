import pytest
from pydantic import ValidationError

from simcc.ai.query_planner import QueryPlan, SearchFilters
from tests.integration.ai.test_live_planner_filters import (
    assert_filter_matches,
)


@pytest.mark.unit
def test_search_filters_defaults():
    """Valida valores padrão e estrutura de SearchFilters."""
    filters = SearchFilters()
    assert filters.institutions == []
    assert filters.researcher_name is None
    assert filters.city is None
    assert filters.identity_territory is None
    assert filters.qualis is None


@pytest.mark.unit
def test_query_plan_valid_structure():
    """Valida instanciação e serialização de QueryPlan
    com identity_territory e qualis.
    """
    plan = QueryPlan(
        intent='researcher_search',
        semantic_query='tecnologia e inovação',
        filters=SearchFilters(
            institutions=['UFBA', 'UNEB'],
            identity_territory='Portal do Sertão',
            qualis=['A1', 'A2'],
        ),
    )
    assert plan.intent == 'researcher_search'
    assert len(plan.filters.institutions) == 2  # noqa: PLR2004
    assert plan.filters.identity_territory == 'Portal do Sertão'
    assert plan.filters.qualis == ['A1', 'A2']

    data = plan.model_dump()
    assert 'institutions' in data['filters']
    assert data['filters']['institutions'] == ['UFBA', 'UNEB']
    assert data['filters']['identity_territory'] == 'Portal do Sertão'
    assert data['filters']['qualis'] == ['A1', 'A2']


@pytest.mark.unit
def test_query_plan_missing_fields():
    """Garante que campos obrigatórios lançam erro de validação."""
    with pytest.raises(ValidationError):
        QueryPlan(
            intent='researcher_search'
        )  # Faltando semantic_query e filters


@pytest.mark.unit
def test_assert_filter_matches_success():
    """Valida que assert_filter_matches passa quando os filtros batem."""
    plan = QueryPlan(
        intent='production_search',
        semantic_query='artigos sobre IA',
        filters=SearchFilters(
            institutions=['UESC'], production_types=['ARTICLE']
        ),
    )
    # Não deve lançar erro
    assert_filter_matches(
        plan=plan,
        question='Quais artigos sobre IA foram publicados pela UESC?',
        filter_category='institutions',
        test_type='Teste combinado',
        expected_filters={
            'institutions': 'UESC',
            'production_types': 'ARTICLE',
        },
    )


@pytest.mark.unit
def test_assert_filter_matches_failure_formats_table():
    """Valida que assert_filter_matches lança AssertionError com tabela."""
    plan = QueryPlan(
        intent='production_search',
        semantic_query='artigos',
        filters=SearchFilters(
            institutions=['UESC'], production_types=[]  # Falta ARTICLE
        ),
    )

    with pytest.raises(AssertionError) as exc_info:
        assert_filter_matches(
            plan=plan,
            question='Quais artigos sobre IA foram publicados pela UESC?',
            filter_category='institutions',
            test_type='Teste combinado',
            expected_filters={
                'institutions': 'UESC',
                'production_types': 'ARTICLE',
            },
        )

    err_msg = str(exc_info.value)
    assert '🚨 FALHA NA EXTRAÇÃO DOS FILTROS ESTRUTURADOS' in err_msg
    assert 'Valor Esperado' in err_msg
    assert 'Valor Obtido no Plano' in err_msg
    assert '❌ FALHOU' in err_msg
    assert 'production_types' in err_msg
    assert 'ARTICLE' in err_msg
    assert 'Referência de Filtros Solicitada' in err_msg
