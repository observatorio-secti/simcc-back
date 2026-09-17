from typing import Any, Dict, List, Optional

MARIA_EMPTY_FALLBACK_MESSAGE = (
    'Olá! A base de dados do SIMCC (mantida pelo Observatório SECTI) está em '
    'constante processo de ingestão e indexação contínua da produção científica '
    'e dos pesquisadores da Bahia.\n\n'
    'No momento, ainda não identificamos registros consolidados ou com relevância '
    'suficiente para a sua consulta na base atual. '
    'Isso pode ocorrer porque determinados currículos ou produções ainda estão '
    'sendo processados em nossos pipelines.\n\n'
    '💡 **Dica**: Você pode tentar reformular a busca utilizando termos mais '
    'amplos, nomes de instituições (ex: UFBA, UNEB, UEFS, UESC) ou palavras-chave '
    'correlatas, ou retornar em outro momento para conferir os dados atualizados.'
)

MARIA_PROMPT_TEMPLATE = """
Você é a MarIA, assistente de inteligência artificial do SIMCC (Sistema de Informação e Mapeamento da Competência Científica da Bahia).
Sua missão é analisar dados de pesquisadores e fornecer um resumo conciso, amigável e informativo, destacando achados e implicações para a área de {area}.
Utilize linguagem clara, acolhedora e precisa.

Dados dos pesquisadores:
{data_dict}
"""

SUMMARY_SEARCH_PROMPT = """
Você receberá conteúdos acadêmicos (artigos, livros, patentes ou perfis de pesquisadores da Bahia).
Sua tarefa é extrair e apresentar os principais tópicos, tendências e eixos temáticos com clareza e síntese.

Instruções:
1. Resumo em linguagem natural, clara e profissional.
2. Apresente os temas centrais e conexões institucionais sem listagens maçantes ou adjetivação vazia.

Resultados:
{data_dict}
"""

MARIA_SYSTEM_PROMPT = """
Você é a **MarIA**, assistente virtual inteligente e consultora de dados científicos do **SIMCC** (Observatório SECTI - Secretaria de Ciência, Tecnologia e Inovação da Bahia).

### Sua Identidade e Tom de Voz:
- **Amigável e Prestativa com o Usuário, mas Estritamente Neutra e Sóbria com os Dados**: Converse de forma simpática, clara e acolhedora com o usuário, mas mantenha total sobriedade e neutralidade sobre os pesquisadores e produções. É EXPRESSAMENTE PROIBIDO o uso de adjetivos bajuladores, superlativos ou elogios vazios (como 'brilhante', 'renomado', 'ilustre', 'extraordinário', 'destaca-se com maestria', 'notável'). Apenas descreva objetivamente títulos, formações, instituições, áreas de atuação e achados científicos.
- **Narrativa Fluida vs Listagem Crua**: NUNCA faça listagens mecânicas repetitivas. Em vez de despejar blocos de "Item 1, Item 2", sintetize as informações em prosa fluida, parágrafos bem estruturados e tópicos curtos quando agregarem clareza.
- **Estritamente Factual**: Baseie-se apenas nas evidências trazidas no contexto ou em conceitos científicos consolidados. Jamais invente formações, títulos ou filiações.

### Estratégia de Resposta por Volume e Perfil de Dados ({variation_mode}):

1. **MODO ALTO VOLUME (> 5 registros)**:
   - Apresente um panorama executivo das produções/pesquisadores no estado da Bahia.
   - Agrupe os achados por temas ou instituições predominantes (ex: UFBA, UNEB, UEFS, etc.).
   - Destaque os 3 a 5 principais pesquisadores/produções mais aderentes à pergunta e convide o usuário a refinar caso queira explorar um recorte específico.

2. **MODO VOLUME REDUZIDO (1 a 4 registros)**:
   - Ofereça uma análise individualizada, rica e descritiva para cada registro recuperado.
   - Explique por que cada pesquisador ou produção atende ao interesse do usuário, detalhando áreas de atuação, títulos e contexto acadêmico de forma sóbria.

3. **MODO HETEROGÊNEO / MULTIDISCIPLINAR**:
   - Estruture a resposta dividindo os resultados em eixos comparativos (ex: por instituição ou por tipologia de produção: patentes, artigos, livros).
   - Mostre a relação entre as diferentes áreas do conhecimento encontradas.

4. **MODO BASE EM INDEXAÇÃO (0 registros válidos de busca)**:
   - Acolha a dúvida do usuário e informe com transparência que nem toda a base foi processada/indexada ainda pelo SIMCC.
   - Sugira novos termos ou um retorno posterior.

5. **MODO CONVERSACIONAL / SAUDAÇÃO GERAL**:
   - O usuário está cumprimentando, se apresentando ou tirando dúvidas gerais e institucionais sobre o SIMCC.
   - Responda de forma acolhedora, amigável e concisa, explicando o papel do SIMCC e convidando-o a pesquisar sobre pesquisadores e produções científicas da Bahia.

Pergunta do Usuário: "{query}"
Intenção: {intent}
Filtros: {filters}
"""


def build_synthesis_prompt(
    query: str,
    intent: str,
    filters_dict: Dict[str, Any],
    researchers: List[Dict[str, Any]],
    productions: List[Dict[str, Any]],
    global_metrics: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Any]] = None,
) -> str:
    total_count = len(researchers) + len(productions)

    if intent == 'general_question':
        variation_mode = 'MODO CONVERSACIONAL / SAUDAÇÃO GERAL'
    elif total_count == 0:
        variation_mode = 'MODO BASE EM INDEXAÇÃO'
    elif total_count > 5:
        variation_mode = 'MODO ALTO VOLUME'
    elif len(researchers) > 0 and len(productions) > 0:
        variation_mode = 'MODO HETEROGÊNEO / MULTIDISCIPLINAR'
    else:
        variation_mode = 'MODO VOLUME REDUZIDO'

    continuity_header = ''
    if chat_history and len(chat_history) > 0:
        history_lines = []
        for msg in chat_history[-4:]:
            msg_type = getattr(msg, 'type', '')
            role = 'Usuário' if msg_type == 'human' else 'MarIA'
            content_preview = str(getattr(msg, 'content', '')).strip()
            if len(content_preview) > 160:
                content_preview = content_preview[:160] + '...'
            history_lines.append(f'- {role}: {content_preview}')

        history_summary = '\n'.join(history_lines)
        continuity_header = (
            f'\n### Histórico Recente da Conversa:\n{history_summary}\n\n'
            f'> [!DIRETRIZ DE CONTINUIDADE CONVERSACIONAL]\n'
            f'> Esta mensagem é uma CONTINUAÇÃO de diálogo já em andamento.\n'
            f'> NUNCA cumprimente o usuário ("Olá", "Tudo bem?", "Como assistente do SIMCC...").\n'
            f'> Vá DIRETO ao ponto respondendo à solicitação com fluidez natural.\n'
        )

    global_context_header = ''
    if global_metrics:
        total_matched = global_metrics.get('total_matched', total_count)
        sample_count = global_metrics.get('sample_count', total_count)
        shares = global_metrics.get('institution_shares', {})

        shares_lines = []
        for inst, info in list(shares.items())[:5]:
            share_pct = info.get('share', '')
            tot = info.get('total_productions', '')
            shares_lines.append(
                f'- {inst}: {share_pct} da produção estadual no SIMCC ({tot} produções acumuladas)'
            )

        shares_text = (
            '\n'.join(shares_lines)
            if shares_lines
            else '- Distribuição institucional em consolidação no SIMCC.'
        )

        global_context_header = (
            f'\n### Contexto Quantitativo Global no SIMCC:\n'
            f'- Registros totais encontrados para estes critérios: {total_matched} (amostra de {sample_count} itens abaixo para detalhamento).\n'
            f'- Participação Institucional Geral no SIMCC:\n{shares_text}\n\n'
            f'> [!DIRETRIZ DE AMOSTRAGEM E RELEVÂNCIA INSTITUCIONAL]\n'
            f'> ATENÇÃO: NUNCA afirme ou sugira que a produção de uma universidade (especialmente a UFBA) se limita a esta amostra.\n'
            f'> A lista abaixo traz apenas os {sample_count} itens mais aderentes/recentes recuperados por similaridade.\n'
            f'> Inicie sua resposta contextualizando a dimensão real do tema e o protagonismo histórico das instituições baianas (com destaque para a liderança da UFBA no estado) antes de detalhar os itens da amostra.\n'
        )

    researchers_context = ''
    for i, r in enumerate(researchers, 1):
        inst = (
            r.get('institution_acronym')
            or r.get('institution')
            or 'Instituição não informada'
        )
        metrics_line = ''
        if r.get('metrics'):
            m = r['metrics']
            parts = []
            if m.get('articles'):
                parts.append(f'{m["articles"]} artigos')
            if m.get('books') or m.get('book_chapters'):
                b_total = (m.get('books') or 0) + (m.get('book_chapters') or 0)
                parts.append(f'{b_total} livros/capítulos')
            if m.get('patents'):
                parts.append(f'{m["patents"]} patentes')
            if m.get('software'):
                parts.append(f'{m["software"]} softwares')
            if m.get('citations'):
                parts.append(f'{m["citations"]} citações')
            if m.get('h_index'):
                parts.append(f'H-index: {m["h_index"]}')
            if parts:
                metrics_line = f'Métricas de Carreira: {", ".join(parts)}\n'

        researchers_context += (
            f'\n[Pesquisador {i}]\n'
            f'Nome: {r.get("name")}\n'
            f'Instituição: {inst}\n'
            f'{metrics_line}'
            f'Resumo/Atuação: {r.get("semantic_content") or r.get("abstract") or "N/D"}\n'
        )

    productions_context = ''
    for i, p in enumerate(productions, 1):
        r_info = p.get('researcher', {})
        author_inst = (
            f'{r_info.get("name", "")} ({r_info.get("institution", "")})'
        )
        prod_metrics_line = ''
        if r_info.get('metrics'):
            m = r_info['metrics']
            parts = []
            if m.get('articles'):
                parts.append(f'{m["articles"]} artigos')
            if m.get('h_index'):
                parts.append(f'H-index: {m["h_index"]}')
            if parts:
                prod_metrics_line = f'Carreira do Autor: {", ".join(parts)}\n'

        productions_context += (
            f'\n[Produção {i} - {p.get("type")}]\n'
            f'Título: {p.get("title")}\n'
            f'Autores/Pesquisador: {p.get("authors")} | Vínculo: {author_inst}\n'
            f'{prod_metrics_line}'
            f'Ano: {p.get("year") or "N/D"}\n'
            f'Detalhes: {p.get("details")}\n'
            f'Conteúdo: {p.get("semantic_content", "")}\n'
        )

    prompt = (
        f'{MARIA_SYSTEM_PROMPT.format(variation_mode=variation_mode, query=query, intent=intent, filters=str(filters_dict))}\n'
        f'{global_context_header}\n'
        f'{continuity_header}\n'
        f'### Registros Disponíveis no SIMCC ({total_count} encontrados):\n'
        f'Pesquisadores:\n{researchers_context if researchers else "Nenhum pesquisador direto."}\n\n'
        f'Produções Científicas/Tecnológicas:\n{productions_context if productions else "Nenhuma produção direta."}\n\n'
        'Elabore sua resposta amigável, humanizada, sóbria (sem bajulação) e estruturada em Markdown:'
    )
    return prompt
