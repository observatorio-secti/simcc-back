from langchain_core.messages import AIMessage, HumanMessage

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


def test_build_synthesis_prompt_with_global_metrics():
    researchers = [
        {
            'name': 'Dr. Silva',
            'institution': 'UFBA',
            'metrics': {
                'articles': 85,
                'patents': 4,
                'h_index': 18,
                'citations': 1200,
            },
        }
    ]
    productions = [
        {
            'title': 'Redes Neurais na Bahia',
            'type': 'ARTICLE',
            'researcher': {
                'name': 'Dr. Silva',
                'institution': 'UFBA',
                'metrics': {'articles': 85, 'h_index': 18},
            },
        }
    ]
    global_metrics = {
        'total_matched': 1420,
        'sample_count': 1,
        'institution_shares': {
            'UFBA': {'total_productions': 980, 'share': '69.0%'},
            'UNEB': {'total_productions': 240, 'share': '16.9%'},
        },
    }

    prompt = build_synthesis_prompt(
        query='Artigos sobre redes neurais',
        intent='production_search',
        filters_dict={},
        researchers=researchers,
        productions=productions,
        global_metrics=global_metrics,
    )

    assert 'Contexto Quantitativo Global no SIMCC' in prompt
    assert '1420' in prompt
    assert 'UFBA: 69.0%' in prompt
    assert 'NUNCA afirme ou sugira que a produção' in prompt
    assert 'Métricas de Carreira: 85 artigos, 4 patentes' in prompt
    assert 'H-index: 18' in prompt


def test_build_synthesis_prompt_with_chat_history():
    history = [
        HumanMessage(content='Como está o perfil de Eduardo Jorge?'),
        AIMessage(content='Encontrei o perfil de Eduardo Manuel na UNEB.'),
    ]

    prompt = build_synthesis_prompt(
        query='Pode me trazer os artigos de Eduardo?',
        intent='production_search',
        filters_dict={'researcher_name': 'Eduardo Manuel de Freitas Jorge'},
        researchers=[],
        productions=[{'title': 'Artigo Teste', 'type': 'ARTICLE'}],
        chat_history=history,
    )

    assert 'Histórico Recente da Conversa:' in prompt
    assert 'Como está o perfil de Eduardo Jorge?' in prompt
    assert 'DIRETRIZ DE CONTINUIDADE CONVERSACIONAL' in prompt
    assert 'NUNCA cumprimente o usuário ("Olá", "Tudo bem?"' in prompt
    assert 'Vá DIRETO ao ponto' in prompt
