import pytest


# ==============================================================================
# 1. researcher_search
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_researcher_search_uesc(live_planner):
    """
    Prompt: "Liste os docentes da UESC que publicam sobre inteligência artificial."
    Valida: Classificação 'researcher_search' e extração da instituição UESC.
    """
    plan = await live_planner.plan(
        'Liste os docentes da UESC que publicam sobre inteligência artificial.'
    )

    assert plan.intent == 'researcher_search'
    institutions = [i.upper() for i in plan.filters.institutions]
    assert any('UESC' in inst for inst in institutions)


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_researcher_search_ufrb(live_planner):
    """
    Prompt: "Encontre pesquisadores com atuação em energia solar na UFRB."
    Valida: Classificação 'researcher_search' e extração da instituição UFRB.
    """
    plan = await live_planner.plan(
        'Encontre pesquisadores com atuação em energia solar na UFRB.'
    )

    assert plan.intent == 'researcher_search'
    institutions = [i.upper() for i in plan.filters.institutions]
    assert any('UFRB' in inst for inst in institutions)


# ==============================================================================
# 2. production_search
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_production_search_fiocruz_dengue(live_planner):
    """
    Prompt: "Quais artigos sobre dengue foram publicados por pesquisadores da Fiocruz Bahia nos últimos três anos?"
    Valida: Classificação 'production_search' e extração do tipo ARTICLE.
    """
    plan = await live_planner.plan(
        'Quais artigos sobre dengue foram publicados por pesquisadores '
        'da Fiocruz Bahia nos últimos três anos?'
    )

    assert plan.intent == 'production_search'
    assert 'ARTICLE' in plan.filters.production_types


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_production_search_uefs_software(live_planner):
    """
    Prompt: "Mostre os softwares registrados por membros da UEFS."
    Valida: Classificação 'production_search', tipo SOFTWARE e instituição UEFS.
    """
    plan = await live_planner.plan(
        'Mostre os softwares registrados por membros da UEFS.'
    )

    assert plan.intent == 'production_search'
    assert 'SOFTWARE' in plan.filters.production_types
    institutions = [i.upper() for i in plan.filters.institutions]
    assert any('UEFS' in inst for inst in institutions)


# ==============================================================================
# 3. researcher_profile
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_researcher_profile_jaqueline_goes(live_planner):
    """
    Prompt: "Apresente o resumo do currículo Lattes da pesquisadora Jaqueline Goes de Jesus."
    Valida: Classificação 'researcher_profile' e extração do nome 'Jaqueline'.
    """
    plan = await live_planner.plan(
        'Apresente o resumo do currículo Lattes da pesquisadora '
        'Jaqueline Goes de Jesus.'
    )

    assert plan.intent == 'researcher_profile'
    assert plan.filters.researcher_name is not None
    assert 'Jaqueline' in plan.filters.researcher_name


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_researcher_profile_jailson_bittencourt(
    live_planner,
):
    """
    Prompt: "Qual é a formação e o histórico acadêmico de Jailson Bittencourt de Andrade?"
    Valida: Classificação 'researcher_profile' e extração do nome 'Jailson'.
    """
    plan = await live_planner.plan(
        'Qual é a formação e o histórico acadêmico de Jailson '
        'Bittencourt de Andrade?'
    )

    assert plan.intent == 'researcher_profile'
    assert plan.filters.researcher_name is not None
    assert 'Jailson' in plan.filters.researcher_name


# ==============================================================================
# 4. aggregation
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_aggregation_uesb_patents(live_planner):
    """
    Prompt: "Qual é o total de patentes depositadas pela UESB até o momento?"
    Valida: Classificação 'aggregation' e extração da instituição UESB.
    """
    plan = await live_planner.plan(
        'Qual é o total de patentes depositadas pela UESB até o momento?'
    )

    assert plan.intent == 'aggregation'
    institutions = [i.upper() for i in plan.filters.institutions]
    assert any('UESB' in inst for inst in institutions)


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_aggregation_books_period(live_planner):
    """
    Prompt: "Quantos livros foram publicados por pesquisadores baianos entre 2020 e 2024?"
    Valida: Classificação 'aggregation' e extração do tipo BOOK.
    """
    plan = await live_planner.plan(
        'Quantos livros foram publicados por pesquisadores baianos '
        'entre 2020 e 2024?'
    )

    assert plan.intent == 'aggregation'
    assert 'BOOK' in plan.filters.production_types


# ==============================================================================
# 5. general_question
# ==============================================================================


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_general_question_capabilities(live_planner):
    """
    Prompt: "Bom dia! Quais tipos de dados acadêmicos você consegue consultar?"
    Valida: Classificação 'general_question'.
    """
    plan = await live_planner.plan(
        'Bom dia! Quais tipos de dados acadêmicos você consegue consultar?'
    )

    assert plan.intent == 'general_question'


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_live_planner_general_question_simcc_explanation(live_planner):
    """
    Prompt: "O que é o SIMCC e como funciona a busca por pesquisadores?"
    Valida: Classificação 'general_question'.
    """
    plan = await live_planner.plan(
        'O que é o SIMCC e como funciona a busca por pesquisadores?'
    )

    assert plan.intent == 'general_question'
