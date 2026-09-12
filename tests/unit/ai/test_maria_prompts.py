from simcc.ai.prompts.maria_prompts import (
    MARIA_EMPTY_FALLBACK_MESSAGE,
    build_synthesis_prompt,
)


def test_build_synthesis_prompt_empty_results():
    prompt = build_synthesis_prompt(
        query='Astroturismo quântico na Bahia',
        intent='researcher_search',
        filters_dict={},
        researchers=[],
        productions=[],
    )
    assert 'MODO BASE EM INDEXAÇÃO' in prompt
    assert 'Astroturismo quântico na Bahia' in prompt
    assert 'MarIA' in prompt


def test_build_synthesis_prompt_high_volume():
    researchers = [
        {'name': f'Pesquisador {i}', 'institution_acronym': 'UFBA'}
        for i in range(6)
    ]
    prompt = build_synthesis_prompt(
        query='Inteligência artificial aplicada à saúde',
        intent='researcher_search',
        filters_dict={'institutions': ['UFBA']},
        researchers=researchers,
        productions=[],
    )
    assert 'MODO ALTO VOLUME' in prompt
    assert 'Pesquisador 1' in prompt


def test_build_synthesis_prompt_low_volume():
    researchers = [
        {'name': 'Dra. Maria Santos', 'institution_acronym': 'UNEB'}
    ]
    prompt = build_synthesis_prompt(
        query='Estudos em literatura baiana',
        intent='researcher_profile',
        filters_dict={},
        researchers=researchers,
        productions=[],
    )
    assert 'MODO VOLUME REDUZIDO' in prompt
    assert 'Dra. Maria Santos' in prompt


def test_build_synthesis_prompt_heterogeneous():
    researchers = [{'name': 'Prof. Carlos', 'institution': 'UFBA'}]
    productions = [{'title': 'Artigo sobre Dengue', 'type': 'ARTICLE'}]
    prompt = build_synthesis_prompt(
        query='Epidemiologia e dengue',
        intent='production_search',
        filters_dict={},
        researchers=researchers,
        productions=productions,
    )
    assert 'MODO HETEROGÊNEO / MULTIDISCIPLINAR' in prompt


def test_empty_fallback_message_content():
    assert 'Observatório SECTI' in MARIA_EMPTY_FALLBACK_MESSAGE
    assert 'constante processo de ingestão' in MARIA_EMPTY_FALLBACK_MESSAGE


def test_build_synthesis_prompt_general_question():
    prompt = build_synthesis_prompt(
        query='Olá! Como você funciona?',
        intent='general_question',
        filters_dict={},
        researchers=[],
        productions=[],
    )
    assert 'MODO CONVERSACIONAL / SAUDAÇÃO GERAL' in prompt
    assert 'Olá! Como você funciona?' in prompt
    assert 'sem bajulação' in prompt
