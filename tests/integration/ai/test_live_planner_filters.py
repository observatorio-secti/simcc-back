# ruff: noqa: E501
import unicodedata
from typing import Any, Dict

import pytest

from simcc.ai.query_planner import QueryPlan

REFERENCE_TABLE = """| Filtro             | Teste isolado                                                                                         | Teste combinado                                                                                                       |
| ------------------ | ----------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| institutions       | "Liste os pesquisadores da UESC que atuam em inteligência artificial." → UESC                        | "Quais artigos sobre inteligência artificial foram publicados por pesquisadores da UESC?" → UESC + ARTICLE            |
| researcher_name    | "Apresente o perfil acadêmico da pesquisadora Jaqueline Goes de Jesus." → Jaqueline Goes de Jesus     | "Apresente o perfil acadêmico de Jaqueline Goes de Jesus, pesquisadora da UFBA." → Jaqueline Goes de Jesus + UFBA     |
| production_types   | "Quais patentes foram registradas por pesquisadores baianos?" → PATENT                                | "Mostre os softwares registrados por pesquisadores da UEFS." → SOFTWARE + UEFS                                        |
| city               | "Quais pesquisadores atuam em Salvador?" → Salvador                                                   | "Quais artigos foram publicados por pesquisadores de Feira de Santana?" → Feira de Santana + ARTICLE                  |
| year_from          | "Quais artigos foram publicados a partir de 2022?" → year_from=2022                                   | "Quais artigos foram publicados a partir de 2022 por pesquisadores da UFBA?" → year_from=2022 + UFBA                  |
| year_to            | "Quais artigos foram publicados até 2020?" → year_to=2020                                             | "Quantos livros foram publicados até 2024?" → year_to=2024 + BOOK                                                     |"""


def _normalize(text: str) -> str:
    """Remove acentos e converte para minúsculas."""
    if not text:
        return ''
    return ''.join(
        c
        for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()


def _generate_failure_report(
    rows: list,
    question: str,
    filter_category: str,
    test_type: str,
    plan: QueryPlan,
) -> str:
    """Gera tabela visual e detalhes diagnósticos para exibição no terminal."""
    col1_w = max(len('Filtro Testado'), *(len(r[0]) for r in rows))
    col2_w = max(len('Valor Esperado'), *(len(r[1]) for r in rows))
    col3_w = max(len('Valor Obtido no Plano'), *(len(r[2]) for r in rows))
    col4_w = 10

    sep = f"+{'-' * (col1_w + 2)}+{'-' * (col2_w + 2)}+{'-' * (col3_w + 2)}+{'-' * (col4_w + 2)}+"
    header = (
        f"| {'Filtro Testado'.ljust(col1_w)} | "
        f"{'Valor Esperado'.ljust(col2_w)} | "
        f"{'Valor Obtido no Plano'.ljust(col3_w)} | "
        f"{'Status'.ljust(col4_w)} |"
    )

    table_lines = [sep, header, sep]
    for r in rows:
        table_lines.append(
            f"| {r[0].ljust(col1_w)} | "
            f"{r[1].ljust(col2_w)} | "
            f"{r[2].ljust(col3_w)} | "
            f"{r[3].ljust(col4_w)} |"
        )
    table_lines.append(sep)
    table_str = '\n'.join(table_lines)

    return (
        f"\n{'=' * 80}\n"
        f"🚨 FALHA NA EXTRAÇÃO DOS FILTROS ESTRUTURADOS\n"
        f"{'=' * 80}\n"
        f"Pergunta   : \"{question}\"\n"
        f"Filtro     : {filter_category}\n"
        f"Modalidade : {test_type}\n\n"
        f"{table_str}\n\n"
        f"Dados Completos do Plano Extraído:\n"
        f"  • Intent:         {plan.intent}\n"
        f"  • Semantic Query: {plan.semantic_query}\n"
        f"  • Filtros:        {plan.filters.model_dump()}\n\n"
        f"Referência de Filtros Solicitada:\n"
        f"{REFERENCE_TABLE}\n"
        f"{'=' * 80}\n"
    )


def assert_filter_matches(
    plan: QueryPlan,
    question: str,
    filter_category: str,
    test_type: str,
    expected_filters: Dict[str, Any],
) -> None:
    """
    Valida os filtros estruturados extraídos pelo QueryPlanner.
    Se qualquer filtro esperado não bater ou estiver ausente, imprime
    uma tabela comparativa detalhada no terminal e lança AssertionError.
    """
    failures = []
    rows = []
    filters = plan.filters

    for key, expected in expected_filters.items():
        actual_val = getattr(filters, key, None)
        matched = False

        if key == 'institutions':
            actual_list = [inst.upper() for inst in (actual_val or [])]
            matched = any(expected.upper() in inst for inst in actual_list)
        elif key == 'production_types':
            actual_list = [prod.upper() for prod in (actual_val or [])]
            matched = expected.upper() in actual_list
        elif key == 'researcher_name':
            if actual_val:
                norm_actual = _normalize(actual_val)
                norm_expected = _normalize(str(expected))
                matched = norm_expected in norm_actual or any(
                    token in norm_actual
                    for token in ['jaqueline', 'goes', 'jesus']
                )
        elif key == 'city':
            if actual_val:
                norm_actual = _normalize(actual_val)
                norm_expected = _normalize(str(expected))
                matched = norm_expected in norm_actual
        elif key in {'year_from', 'year_to'}:
            matched = actual_val == expected
        else:
            matched = actual_val == expected

        status = '✅ OK' if matched else '❌ FALHOU'
        if not matched:
            failures.append(key)

        rows.append((key, str(expected), str(actual_val), status))

    if failures:
        report = _generate_failure_report(
            rows, question, filter_category, test_type, plan
        )
        print(report, flush=True)
        raise AssertionError(report)

    print(f"\n[PASS] {filter_category} ({test_type}) -> Filtros conferem!", flush=True)


# ==============================================================================
# 1. institutions
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_institutions_isolated(live_planner):
    """
    Prompt: "Liste os pesquisadores da UESC que atuam em inteligência artificial."
    Filtro isolado: UESC em institutions.
    """
    question = (
        'Liste os pesquisadores da UESC que atuam em inteligência artificial.'
    )
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='institutions',
        test_type='Teste isolado',
        expected_filters={'institutions': 'UESC'},
    )


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_institutions_combined(live_planner):
    """
    Prompt: "Quais artigos sobre inteligência artificial foram publicados por pesquisadores da UESC?"
    Filtro combinado: UESC em institutions + ARTICLE em production_types.
    """
    question = (
        'Quais artigos sobre inteligência artificial foram publicados por '
        'pesquisadores da UESC?'
    )
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='institutions',
        test_type='Teste combinado',
        expected_filters={
            'institutions': 'UESC',
            'production_types': 'ARTICLE',
        },
    )


# ==============================================================================
# 2. researcher_name
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_researcher_name_isolated(live_planner):
    """
    Prompt: "Apresente o perfil acadêmico da pesquisadora Jaqueline Goes de Jesus."
    Filtro isolado: Jaqueline Goes de Jesus em researcher_name.
    """
    question = (
        'Apresente o perfil acadêmico da pesquisadora Jaqueline Goes de Jesus.'
    )
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='researcher_name',
        test_type='Teste isolado',
        expected_filters={'researcher_name': 'Jaqueline Goes de Jesus'},
    )


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_researcher_name_combined(live_planner):
    """
    Prompt: "Apresente o perfil acadêmico de Jaqueline Goes de Jesus, pesquisadora da UFBA."
    Filtro combinado: Jaqueline Goes de Jesus em researcher_name + UFBA em institutions.
    """
    question = (
        'Apresente o perfil acadêmico de Jaqueline Goes de Jesus, '
        'pesquisadora da UFBA.'
    )
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='researcher_name',
        test_type='Teste combinado',
        expected_filters={
            'researcher_name': 'Jaqueline Goes de Jesus',
            'institutions': 'UFBA',
        },
    )


# ==============================================================================
# 3. production_types
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_production_types_isolated(live_planner):
    """
    Prompt: "Quais patentes foram registradas por pesquisadores baianos?"
    Filtro isolado: PATENT em production_types.
    """
    question = 'Quais patentes foram registradas por pesquisadores baianos?'
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='production_types',
        test_type='Teste isolado',
        expected_filters={'production_types': 'PATENT'},
    )


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_production_types_combined(live_planner):
    """
    Prompt: "Mostre os softwares registrados por pesquisadores da UEFS."
    Filtro combinado: SOFTWARE em production_types + UEFS em institutions.
    """
    question = 'Mostre os softwares registrados por pesquisadores da UEFS.'
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='production_types',
        test_type='Teste combinado',
        expected_filters={
            'production_types': 'SOFTWARE',
            'institutions': 'UEFS',
        },
    )


# ==============================================================================
# 4. city
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_city_isolated(live_planner):
    """
    Prompt: "Quais pesquisadores atuam em Salvador?"
    Filtro isolado: Salvador em city.
    """
    question = 'Quais pesquisadores atuam em Salvador?'
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='city',
        test_type='Teste isolado',
        expected_filters={'city': 'Salvador'},
    )


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_city_combined(live_planner):
    """
    Prompt: "Quais artigos foram publicados por pesquisadores de Feira de Santana?"
    Filtro combinado: Feira de Santana em city + ARTICLE em production_types.
    """
    question = (
        'Quais artigos foram publicados por pesquisadores de Feira de Santana?'
    )
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='city',
        test_type='Teste combinado',
        expected_filters={
            'city': 'Feira de Santana',
            'production_types': 'ARTICLE',
        },
    )


# ==============================================================================
# 5. year_from
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_year_from_isolated(live_planner):
    """
    Prompt: "Quais artigos foram publicados a partir de 2022?"
    Filtro isolado: year_from=2022.
    """
    question = 'Quais artigos foram publicados a partir de 2022?'
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='year_from',
        test_type='Teste isolado',
        expected_filters={'year_from': 2022},
    )


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_year_from_combined(live_planner):
    """
    Prompt: "Quais artigos foram publicados a partir de 2022 por pesquisadores da UFBA?"
    Filtro combinado: year_from=2022 + UFBA em institutions.
    """
    question = (
        'Quais artigos foram publicados a partir de 2022 por pesquisadores da '
        'UFBA?'
    )
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='year_from',
        test_type='Teste combinado',
        expected_filters={
            'year_from': 2022,
            'institutions': 'UFBA',
        },
    )


# ==============================================================================
# 6. year_to
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_year_to_isolated(live_planner):
    """
    Prompt: "Quais artigos foram publicados até 2020?"
    Filtro isolado: year_to=2020.
    """
    question = 'Quais artigos foram publicados até 2020?'
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='year_to',
        test_type='Teste isolado',
        expected_filters={'year_to': 2020},
    )


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_filter_year_to_combined(live_planner):
    """
    Prompt: "Quantos livros foram publicados até 2024?"
    Filtro combinado: year_to=2024 + BOOK em production_types.
    """
    question = 'Quantos livros foram publicados até 2024?'
    plan = await live_planner.plan(question)

    assert_filter_matches(
        plan=plan,
        question=question,
        filter_category='year_to',
        test_type='Teste combinado',
        expected_filters={
            'year_to': 2024,
            'production_types': 'BOOK',
        },
    )
