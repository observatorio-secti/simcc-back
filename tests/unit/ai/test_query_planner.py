import pytest
from pydantic import ValidationError

from simcc.ai.query_planner import QueryPlan, SearchFilters


@pytest.mark.unit
def test_search_filters_defaults():
    """Valida valores padrão e estrutura de SearchFilters."""
    filters = SearchFilters()
    assert filters.institutions == []
    assert filters.researcher_name is None
    assert filters.city is None


@pytest.mark.unit
def test_query_plan_valid_structure():
    """Valida instanciação e serialização de QueryPlan."""
    plan = QueryPlan(
        intent='researcher_search',
        semantic_query='tecnologia e inovação',
        filters=SearchFilters(institutions=['UFBA', 'UNEB']),
    )
    assert plan.intent == 'researcher_search'
    assert len(plan.filters.institutions) == 2

    data = plan.model_dump()
    assert 'institutions' in data['filters']
    assert data['filters']['institutions'] == ['UFBA', 'UNEB']


@pytest.mark.unit
def test_query_plan_missing_fields():
    """Garante que campos obrigatórios lançam erro de validação."""
    with pytest.raises(ValidationError):
        QueryPlan(
            intent='researcher_search'
        )  # Faltando semantic_query e filters
