"""
topic_hierarchizer.py — Hierarquização de tópicos com estrutura ÁREA/ASSUNTO obrigatória.
 
Para cada tópico gerado pelo BERTopic, este módulo usa um LLM (GPT-4o-mini)
para estruturar o conteúdo em:
  - topic_area: nome acadêmico consolidado da área (ex: "Inteligência Artificial")
  - subtopics: lista de 3-5 assuntos específicos derivados dos abstracts
  - main_areas: áreas da taxonomia sugeridas pelo LLM para ancoragem semântica
  - abstract_coverage: descrição do conteúdo real dos abstracts do tópico
 
A saída é um CSV consumido por graph_topic_integrator.py para integração
no grafo base da taxonomia.

SubtopicArea é uma classe fixa — seus campos são genéricos para qualquer domínio.
AreaPrediction e HierarchicalTopicLabel são construídos dinamicamente a partir do
TaxonomyConfig, pois referenciam o domínio específico da taxonomia em uso.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, create_model

from .taxonomy_config import TaxonomyConfig

logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMA PYDANTIC FIXO
# =============================================================================
class SubtopicArea(BaseModel):
    """Um assunto/subtópico específico dentro de um tópico, estruturado pelo LLM."""
    
    name: str = Field(
        description=(
            "Nome de 2-5 palavras de um assunto específico dentro do tópico. "
            "Exemplos: 'Visão Computacional em Diagnóstico', 'Redes Neurais Convolucionais', "
            "'Otimização de Hiperparâmetros'. Deve refletir o conteúdo real dos abstracts."
        )
    )
    keywords: list[str] = Field(
        description="3-5 palavras-chave principais deste subtópico, extraídas dos abstracts.",
        default_factory=list
    )
    frequency: int = Field(
        description="Quantos abstracts mencionam este assunto (escala aproximada 1-10).",
        default=1
    )


# =============================================================================
# SCHEMAS PYDANTIC DINÂMICOS
# =============================================================================
def _build_schemas(
    config: TaxonomyConfig,
    known_area_names: list[str],            
) -> tuple[type[BaseModel], type[BaseModel]]:
    """
    Constrói AreaPrediction e HierarchicalTopicLabel dinamicamente.
 
    AreaPrediction precisa referenciar o domínio nos Field.description —
    o LLM lê essas descrições via with_structured_output para saber qual
    taxonomia usar na classificação.
 
    HierarchicalTopicLabel precisa ser dinâmico para receber o tipo concreto
    list[AreaPrediction] em main_areas.
    """
    known_areas_str = ", ".join(f"'{a}'" for a in known_area_names) or "(nenhuma área cadastrada ainda)"
 
    AreaPrediction = create_model(
        "AreaPrediction",
        __doc__=(
            f"Área da taxonomia {config.name} à qual este tópico genuinamente se conecta."
        ),
        area_name=(
            str,            
            Field(description=(
                f"Nome em português do Brasil (pt-BR) de UMA área da taxonomia {config.name}. "
                f"Escolha SOMENTE entre estes nomes exatos, sem inventar variações: {known_areas_str}."
            )),
        ),
        confidence=(
            float,
            Field(description="Grau de certeza da classificação (0.0 a 1.0)."),
        ),
    )
 
    HierarchicalTopicLabel = create_model(
        "HierarchicalTopicLabel",
        __doc__="Estrutura hierárquica completa de um tópico, gerada pelo LLM.",
        topic_area=(
            str,            
            Field(description=(
                "OBRIGATÓRIO: Nome de uma ÁREA ou ASSUNTO principal (2-4 palavras), "
                "em português do Brasil (pt-BR). "
                "Exemplos: 'Inteligência Artificial', 'Visão Computacional', 'Aprendizado de Máquina'. "
                "Deve ser um termo acadêmico consolidado, não palavras soltas. "
                f"NÃO PODE ser idêntico ou uma variação óbvia de nenhum destes nomes de área já "
                f"existentes na taxonomia: {known_areas_str} — topic_area representa um TÓPICO "
                "dentro de uma área, não a área em si."
            )),
        ),
        subtopics=(
            Annotated[list[SubtopicArea], Field(min_length=3, max_length=5)],
            Field(description=(
                "Lista de 3-5 ASSUNTOS específicos dentro da área, em português do Brasil (pt-BR). "
                "Cada um tem nome estruturado de 2-5 palavras. "
                "Todos devem existir nos abstracts do tópico."
            )),
        ),
        is_relevant_to_taxonomy=(
            bool,
            Field(description=(
                f"true APENAS se o conteúdo central do tópico genuinamente pertencer ao domínio '{config.domain_description}' "
                f"e se conectar a uma das áreas: {known_areas_str}. "
                "SE O TÓPICO FOR DE OUTRO CAMPO DO CONHECIMENTO (ex: medicina, biologia, saúde, química, agronomia "
                "quando a taxonomia for Tecnologia; ou tecnologia/engenharia quando for Educação), "
                "marque OBRIGATORIAMENTE false e deixe main_areas como lista VAZIA []. "
                "NUNCA force conexões artificiais."
            )),
        ),
        main_areas=(
            Annotated[list[AreaPrediction], Field(max_length=1)],
            Field(description=(
                "Se is_relevant_to_taxonomy=false, retorne OBRIGATORIAMENTE lista VAZIA []. "
                "Se true, retorne EXATAMENTE 1 área dentre as listadas com confidence real (>= 0.60): "
                f"{known_areas_str}. Nunca retorne área com confiança baixa ou inventada."
            )),
        ),
        abstract_coverage=(
            str,            
            Field(description=(
                "Descrição breve (1-2 frases) do que os abstracts deste tópico cobrem, "
                "em português do Brasil (pt-BR). Deve refletir o conteúdo real, não ser genérico."
            )),
        ),
    )
 
    return AreaPrediction, HierarchicalTopicLabel


# =============================================================================
# LLM CHAIN
# =============================================================================
def _build_system_template(config: TaxonomyConfig, known_area_names: list[str]) -> str:
    """
    Constrói o system prompt injetando o domínio do TaxonomyConfig.
 
    Se config.taxonomy_context estiver preenchido (ex: ODS), inclui a
    descrição completa das áreas para que o LLM classifique corretamente
    mesmo sem conhecimento prévio da taxonomia.
    """
    context_block = (
        f"\nCONTEXTO DA TAXONOMIA {config.name.upper()}:\n{config.taxonomy_context}\n"
        if config.taxonomy_context
        else ""
    )
    known_areas_str = ", ".join(f"'{a}'" for a in known_area_names) or "(nenhuma área cadastrada ainda)"
 
    return f"""Você é especialista em taxonomia de conhecimento acadêmico.
{context_block}
TAXONOMIA ALVO: {config.domain_description}
ÁREAS DE NÍVEL 1 JÁ EXISTENTES NESTA TAXONOMIA: {known_areas_str}
 
IDIOMA: Todos os campos de texto da resposta (topic_area, subtopics, main_areas.area_name,
abstract_coverage) devem estar em português do Brasil (pt-BR), mesmo que os abstracts
recebidos estejam em inglês.

REGRAS DE CLASSIFICAÇÃO:
1. topic_area (OBRIGATÓRIO): Sempre ASSUNTO acadêmico (ex: "Inteligência Artificial", "Visão Computacional")
   - NÃO use palavras soltas: "knowledge", "system", "method"
   - NÃO pode coincidir com nenhuma das áreas de nível 1 listadas acima — topic_area é um
     TÓPICO dentro de uma área, não a área em si.
2. subtopics (3-5): Nomes de 2-5 palavras (ex: "Diagnóstico por Imagem", "Otimização de Redes")
3. is_relevant_to_taxonomy (RIGOROSO):
   - Avalie se a essência do tópico pertence ao domínio da taxonomia alvo ({config.domain_description}).
   - Se o tópico for de outra área (ex: saúde, farmacologia, alimentos, química quando a taxonomia for Tecnologia),
     marque OBRIGATORIAMENTE is_relevant_to_taxonomy=false e main_areas=[].
   - Não force conexões superficiais só porque o abstract usou um software ou método estatístico.
4. main_areas:
   - Se is_relevant_to_taxonomy=false: lista VAZIA [].
   - Se is_relevant_to_taxonomy=true: exatamente 1 área dentre as listadas, com confidence >= 0.60.
5. abstract_coverage: Descrição breve do conteúdo real dos artigos.
"""
    
_HUMAN_TEMPLATE = """TÓPICO: {topic_id}
PALAVRAS-CHAVE: {keywords}
TÍTULOS: {titles}
RESUMOS: {abstracts}

Estruture em ÁREA → SUBTÓPICOS.
"""

def _build_chain(llm: ChatOpenAI, config: TaxonomyConfig, known_area_names: list[str]) -> Any:
    """
    Constrói a chain LangChain para hierarquização de tópicos.

    Os schemas são construídos dinamicamente a partir do config — garantindo
    que Field.description e docstrings referenciem o domínio correto.
    """
    _, hierarchical_topic_label = _build_schemas(config, known_area_names)
    structured_llm = llm.with_structured_output(hierarchical_topic_label)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _build_system_template(config, known_area_names)),
        ("human", _HUMAN_TEMPLATE),
    ])

    return prompt | structured_llm


# =============================================================================
# UTILITÁRIOS DE CONSTRUÇÃO DE LINHAS
# =============================================================================
def _build_result_row(
    topic_id: int,
    response: Any,
    num_documents: int,
) -> dict:
    """
    Constrói o dicionário de resultado a partir da resposta estruturada do LLM.
    Serializa subtopics e main_areas como JSON para armazenamento em CSV.
    """
    is_relevant = bool(getattr(response, "is_relevant_to_taxonomy", True))
    main_areas = getattr(response, "main_areas", []) or []

    # Validação de consistência: se confidence < 0.60 ou área vazia, desconsidera relevância
    if is_relevant:
        if not main_areas or (main_areas and getattr(main_areas[0], "confidence", 0.0) < 0.60):
            is_relevant = False
            main_areas = []

    confidence = main_areas[0].confidence if main_areas else (0.0 if not is_relevant else 0.5)

    return {
        "Topic": topic_id,
        "Area": response.topic_area,
        "Subtopics": json.dumps(
            [{"name": st.name, "keywords": st.keywords, "frequency": st.frequency}
             for st in response.subtopics],
            ensure_ascii=False,
        ),
        "Is_Relevant": is_relevant,
        "Main_Areas": json.dumps(
            [{"area": a.area_name, "confidence": a.confidence} for a in main_areas],
            ensure_ascii=False,
        ),
        "Coverage": response.abstract_coverage,
        "Confidence": confidence,
        "Num_Documents": num_documents,
    }
 
 
def _build_fallback_row(
    topic_id: int,
    keywords: str,
    num_documents: int,
) -> dict:
    """
    Constrói uma linha de fallback quando o LLM falha na hierarquização.
    Usa as keywords brutas do BERTopic como substitutos dos assuntos estruturados.
    """
    area = str(keywords).split(",")[0].strip() if keywords else f"Topic_{topic_id}"
    fallback_subtopics = [
        {"name": k.strip(), "keywords": [], "frequency": 1}
        for k in str(keywords).split(",")[:3]
        if k.strip()
    ]
    return {
        "Topic": topic_id,
        "Area": area,
        "Subtopics": json.dumps(fallback_subtopics, ensure_ascii=False),
        "Is_Relevant": True,
        "Main_Areas": "[]",
        "Coverage": "Erro ao processar",
        "Confidence": 0.3,
        "Num_Documents": num_documents,
    }
 
 
def _prepare_topic_context(row: pd.Series) -> tuple[str, str]:
    """
    Extrai títulos e resumos dos documentos REPRESENTATIVOS do tópico
    (selecionados pelo próprio BERTopic via get_representative_docs — os
    documentos semanticamente mais próximos do centróide do tópico).

    Lê a coluna Representative_Docs_JSON, escrita por topic_modeling.py.
    """
    raw = row.get("Representative_Docs_JSON", "[]")
    try:
        docs = json.loads(raw) if isinstance(raw, str) and raw.strip() else []
    except (json.JSONDecodeError, TypeError):
        logger.warning("Representative_Docs_JSON inválido para o tópico %s — ignorado.", row.get("Topic"))
        docs = []

    titles = " || ".join(d.get("title", "") for d in docs if d.get("title"))
    abstracts_text = " || ".join(d.get("abstract", "") for d in docs if d.get("abstract"))
    return titles, abstracts_text


# =============================================================================
# API PÚBLICA
# =============================================================================
def hierarchize_topics(
    input_csv: str | Path,
    mapping_csv: str | Path,
    output_csv: str | Path = "data/processed/topics_hierarchized.csv",
    config: TaxonomyConfig | None = None,
    model_name: str = "gpt-4o-mini",
    known_area_names: list[str] | None = None,
) -> pd.DataFrame:
    """
    Processa tópicos BERTopic e estrutura cada um em Área → Assuntos via LLM.
 
    Para cada tópico em `input_csv`, envia títulos e resumos dos documentos
    associados (via `mapping_csv`) ao LLM e obtém uma estrutura hierárquica
    validada pelo schema construído a partir do TaxonomyConfig.
 
    Tópicos sem documentos associados são ignorados.
    Tópicos em que o LLM falha recebem uma linha de fallback com as keywords
    brutas do BERTopic, garantindo que o CSV de saída seja sempre completo.
    """    
    print(f"\n{'='*60}")
    print("ETAPA 3: Hierarquização de tópicos")
    print(f"{'='*60}\n")

    logger.info("Hierarquização de tópicos com LLM (%s) — taxonomia: %s", model_name, config.name)
    
    df_topics = pd.read_csv(input_csv, encoding="utf-8")
    df_mapping = pd.read_csv(mapping_csv, encoding="utf-8")
    known_area_names = known_area_names or []
    
    # LLM e chain instanciados uma única vez — evita overhead de reconexão
    # a cada tópico e permite reutilizar a mesma sessão HTTP.
    llm = ChatOpenAI(model=model_name, temperature=0)    
    chain = _build_chain(llm, config, known_area_names)
    
    logger.info("Processando %d tópicos...\n", len(df_topics))
    results = []

    for _, row in df_topics.iterrows():
        topic_id = int(row["Topic"])
        keywords = str(row.get("Keywords", ""))
        num_documents = int(row.get("Num_Documents", 0) or 0)

        if num_documents <= 0:
            logger.debug("Tópico %d sem documentos associados — ignorado.", topic_id)
            continue

        titles, abstracts_text = _prepare_topic_context(row)

        try:
            logger.info("Tópico %d — enviando ao LLM...", topic_id)            
            response = chain.invoke({
                "topic_id": topic_id,
                "keywords": keywords,
                "titles": titles,
                "abstracts": abstracts_text
            })
            results.append(_build_result_row(topic_id, response, num_documents))
            logger.info("Tópico %d — estruturado com sucesso ✓.\n", topic_id)
            
        except Exception as e:
            logger.warning(
                "Tópico %d — falha no LLM ✗, usando fallback. Erro: %s", 
                topic_id, str(e)[:50],
                exc_info=True,
            )
            results.append(_build_fallback_row(topic_id, keywords, num_documents))

    
    df_result = pd.DataFrame(results)    
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_result.to_csv(output_path, index=False, encoding="utf-8")
    
    logger.info("✅ %d tópicos hierarquizados salvos em:\n %s\n", len(df_result), output_path)
    return df_result