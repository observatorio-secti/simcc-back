"""
topic_modeling.py - Modelagem de tópicos (BERTopic) a partir de documentos.

Agrupa textos em tópicos temáticos usando BERTopic (UMAP + HDBSCAN +
CountVectorizer) e gera dois CSVs de saída:
  - topics_extracted.csv: tópicos com keywords e documentos representativos
  - topic_document_mapping.csv: mapeamento documento → tópico para rastreabilidade
 
Os tópicos gerados são consumidos por topic_hierarchizer.py, que os estrutura
em Área → Assuntos via LLM, e por graph_topic_integrator.py, que os integra
ao grafo base da taxonomia.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

import nltk
import pandas as pd
from bertopic import BERTopic
from hdbscan import HDBSCAN
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP
from typing import Literal

from .embeddings import DEFAULT_EMBEDDING_MODEL, get_embedding_model

logger = logging.getLogger(__name__)

 
_REP_DOC_LLM_MAX_CHARS = 600  # truncamento p/ o JSON consumido pelo LLM (Representative_Docs continua com 260, só p/ leitura humana)

ReductionStrategy = Literal["none", "auto", "fixed", "similarity_threshold"]


# =============================================================================
# TRADUÇÃO DE KEYWORDS
# =============================================================================

# Mapeamento de frases compostas EN → PT. 
# A ordem importa: frases mais longas devem vir antes das mais curtas, 
# evitando por exemplo que "large language model" se transforme em "large modelo de linguagem".
_PHRASE_MAP: list[tuple[str, str]] = [
    ("large language model", "modelo de linguagem grande"),
    ("language model", "modelo de linguagem"),
    ("artificial intelligence", "inteligência artificial"),
    ("natural language processing", "processamento de linguagem natural"),
    ("computer vision", "visão computacional"),
    ("graph neural network", "rede neural em grafos"),
    ("neural network", "rede neural"),
    ("reinforcement learning", "aprendizado por reforço"),
    ("federated learning", "aprendizado federado"),
    ("transfer learning", "aprendizado por transferência"),
    ("self supervised", "auto-supervisionado"),
    ("self-supervised", "auto-supervisionado"),
    ("deep learning", "aprendizado profundo"),
    ("machine learning", "aprendizado de máquina"),
    ("few shot", "poucos exemplos"),
    ("few-shot", "poucos exemplos"),
    ("one shot", "um exemplo"),
    ("one-shot", "um exemplo"),
    ("fine tuning", "ajuste fino"),
    ("fine-tuning", "ajuste fino"),
    ("data centric", "centrado em dados"),
    ("data-centric", "centrado em dados"),
]
 
# Mapeamento de tokens individuais EN → PT.
_TOKEN_MAP: dict[str, str] = {
    "ai": "IA",
    "ia": "IA",
    "ml": "aprendizado de máquina",
    "intelligence": "inteligência",
    "data": "dados",
    "dataset": "conjunto de dados",
    "training": "treinamento",
    "optimization": "otimização",
    "optimisation": "otimização",
    "model": "modelo",
    "models": "modelos",
    "classification": "classificação",
    "clustering": "agrupamento",
    "prediction": "predição",
    "forecasting": "previsão",
    "detection": "detecção",
    "generation": "geração",
    "robustness": "robustez",
    "fairness": "equidade",
    "explainability": "explicabilidade",
    "explainable": "explicável",
}


def _translate_keyword_pt(text: str) -> str:
    """
    Tradução leve e determinística de termos comuns (principalmente IA/ML).
    Não tenta traduzir tudo; só o suficiente para o LLM receber contexto em PT.

    Aplica primeiro substituições de frases compostas (ex: "deep learning" →
    "aprendizado profundo") e depois substituições token a token. A ordem
    garante que frases compostas sejam traduzidas antes de seus componentes
    individuais, evitando traduções parciais sobrepostas.
    """
    normalized = str(text).strip().lower()
    if not normalized:
        return normalized
    
    for src, dst in _PHRASE_MAP:
        normalized = normalized.replace(src, dst)

    tokens = [_TOKEN_MAP.get(tok, tok) for tok in normalized.split()]
    return " ".join(tokens).strip()


def _translate_keywords_list_pt(keywords: list[str]) -> list[str]:
    """Traduz uma lista de keywords para português, removendo duplicatas."""
    result: list[str] = []
    for kw in keywords:
        translated = _translate_keyword_pt(kw)
        if translated and translated not in result:
            result.append(translated)
    return result


# =============================================================================
# UTILITÁRIOS DE EXTRAÇÃO
# =============================================================================
def _keywords_from_topic(topic_words: list[tuple[str, float]], top_k: int = 5) -> list[str]:
    """
    Extrai as top_k keywords de um tópico BERTopic.
    `topic_words` é uma lista de tuplas (palavra, peso) retornada por get_topic().
    """
    if not topic_words:
        return []
    return [w.strip() for w, _score in topic_words[:top_k] if str(w).strip()]


def _representative_docs_text(rep_docs: list[str], max_docs: int = 3, max_chars: int = 260) -> str:
    """
    Formata os documentos representativos de um tópico em uma string concatenada.
    Trunca cada documento em `max_chars` caracteres para evitar CSVs excessivamente grandes.
    """
    parts = []
    for doc in (rep_docs or [])[:max_docs]:
        doc = str(doc)
        if len(doc) > max_chars:
            doc = doc[:max_chars] + "..."
        parts.append(doc)
    return " || ".join(parts)


def _build_abstract_to_title_lookup(docs_df: pd.DataFrame | None) -> dict[str, str]:
    """
    Constrói abstract (texto exato usado no fit_transform) -> título.

    Os documentos retornados por get_representative_docs() são exatamente as
    strings da lista `documents` passada ao fit_transform (= docs_df['abstract']),
    então o match exato funciona sem necessidade de fuzzy matching.
    """
    if docs_df is None or "abstract" not in docs_df.columns or "title" not in docs_df.columns:
        return {}
    return dict(zip(docs_df["abstract"].astype(str), docs_df["title"].astype(str)))


def _representative_docs_structured(
    rep_docs: list[str],
    abstract_to_title: dict[str, str],
    max_docs: int = 3,
    max_chars: int = _REP_DOC_LLM_MAX_CHARS,
) -> list[dict]:
    """
    Estrutura os documentos representativos do tópico (title + abstract
    truncado) para consumo pelo LLM em topic_hierarchizer.
    """
    structured = []
    for doc in (rep_docs or [])[:max_docs]:
        doc_text = str(doc)
        title = abstract_to_title.get(doc_text, "")
        truncated = doc_text if len(doc_text) <= max_chars else doc_text[:max_chars] + "..."
        structured.append({"title": title, "abstract": truncated})
    return structured


def _build_topic_row(
    topic_id: int,
    row: pd.Series,
    topic_model: BERTopic,
    counts: Counter,
    abstract_to_title: dict[str, str],
) -> dict:
    """
    Constrói o dicionário de uma linha do CSV de tópicos para um único tópico.
 
    Extrai keywords brutas do BERTopic, traduz para português e monta
    os campos de saída compatíveis com topic_hierarchizer.py.
    """
    topic_words = topic_model.get_topic(topic_id)
    top_keywords_raw = _keywords_from_topic(topic_words, top_k=5)
    top_keywords = _translate_keywords_list_pt(top_keywords_raw)
 
    rep_docs = topic_model.get_representative_docs(topic_id) or []
    rep_docs_text = _representative_docs_text(rep_docs)
    rep_docs_structured = _representative_docs_structured(rep_docs, abstract_to_title)

    name = str(row.get("Name") or "").strip() or f"topic_{topic_id}"
    keywords_str_raw = ", ".join(top_keywords_raw)
    keywords_str = ", ".join(top_keywords)
 
    return {
        "Topic": topic_id,
        "Name": name,
        "Num_Documents": int(counts.get(topic_id, 0)),
        "Keywords": keywords_str,
        "Keywords_RAW": keywords_str_raw,
        "Representative_Docs": rep_docs_text,
        "Representative_Docs_JSON": json.dumps(rep_docs_structured, ensure_ascii=False),
    }
 

def _reduce_topics(
    topic_model: BERTopic,
    documents: list[str],
    strategy: ReductionStrategy,
    nr_topics: int | None = None,
    max_distance: float = 0.6,
) -> list[int]:
    """
    Aplica a estratégia de redução de tópicos escolhida e retorna a nova
    atribuição documento -> tópico (topic_model.topics_ já atualizado).

    Estratégias:
    - "none": não reduz, mantém a saída bruta do HDBSCAN.
    - "auto": deixa o BERTopic decidir via meta-clustering (HDBSCAN com
      min_cluster_size=3 sobre as representações c-TF-IDF dos tópicos).
      Só funde tópicos que o próprio algoritmo considera "o mesmo cluster
      de tópicos" — pode não reduzir nada se os tópicos já forem distintos
      entre si (comportamento esperado, não um bug).
    - "fixed": força exatamente `nr_topics` tópicos via clustering
      aglomerativo, fundindo os pares mais similares repetidamente até
      bater a meta — MESMO que a similaridade real seja fraca. Só usar
      se você sabe que quer exatamente N tópicos, aceitando esse risco.
    - "similarity_threshold": funde apenas os pares cuja distância de fusão
      hierárquica (1 - similaridade c-TF-IDF) fica ABAIXO de `max_distance`.
      Não mira um número-alvo — o resultado final pode ser qualquer
      contagem, mas cada fusão aplicada é uma fusão "justificada" pela
      similaridade real entre os tópicos. Recomendado como primeira opção
      quando o objetivo é reduzir redundância sem perder distinções
      semânticas reais.
    """
    if strategy == "none":
        return topic_model.topics_

    if strategy == "auto":
        topic_model.reduce_topics(documents, nr_topics="auto")
        return topic_model.topics_

    if strategy == "fixed":
        if not nr_topics or nr_topics < 1:
            raise ValueError("strategy='fixed' requer nr_topics >= 1.")
        topic_model.reduce_topics(documents, nr_topics=nr_topics)
        return topic_model.topics_

    if strategy == "similarity_threshold":
        hierarchical_topics = topic_model.hierarchical_topics(documents)
        merges_to_apply = hierarchical_topics[hierarchical_topics["Distance"] <= max_distance]

        if merges_to_apply.empty:
            logger.info(
                "Nenhum par de tópicos abaixo do limiar de distância %.3f — nada fundido.",
                max_distance,
            )
            return topic_model.topics_

        groups_to_merge = [row["Topics"] for _, row in merges_to_apply.iterrows()]
        topic_model.merge_topics(documents, groups_to_merge)
        logger.info(
            "✅ %d fusões aplicadas (distância <= %.3f).",
            len(groups_to_merge), max_distance,
        )
        return topic_model.topics_

    raise ValueError(f"Estratégia de redução desconhecida: '{strategy}'")

 
def _build_topic_model(
    min_cluster_size: int,
    min_samples: int,
    n_neighbors: int,
    embedding_model_name: str,
) -> BERTopic:
    """
    Instancia e configura o modelo BERTopic com os hiperparâmetros fornecidos.
 
    Configurações aplicadas para favorecer tópicos mais macro (menos granulares):
    - CountVectorizer: ngrams (1,2), min_df=3 — evita tópicos gerados por termos raros
    - UMAP: n_components=5, metric=cosine — redução dimensional preservando semântica
    - HDBSCAN: cluster_selection_method="eom" — produz menos clusters que "leaf"
    - random_state=42 no UMAP para reprodutibilidade
    """
    nltk.download("stopwords", quiet=True)
    stop_words = set(stopwords.words("portuguese")) | set(stopwords.words("english"))
 
    # Menos granular: evita ngrams longos e termos raros gerando tópicos minúsculos.
    vectorizer_model = CountVectorizer(
        stop_words=list(stop_words),
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.9,
    )
    umap_model = UMAP(
        n_neighbors=n_neighbors,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_method="eom",  # tende a produzir menos clusters que "leaf"
        prediction_data=True,
    )
    embedding_model = get_embedding_model(embedding_model_name)
 
    return BERTopic(
        language="multilingual",
        vectorizer_model=vectorizer_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        embedding_model=embedding_model,
        verbose=True,
    )
 
 
def _save_topic_document_mapping(
    docs_df: pd.DataFrame,
    topics: list[int],
    output_path: Path,
) -> None:
    """
    Persiste o mapeamento documento → tópico em CSV.
    Usado por topic_tracer para rastreabilidade artigo → área.
    """
    df_map = docs_df.copy().reset_index(drop=True)
    df_map["Topic"] = [int(t) for t in topics]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_map.to_csv(output_path, index=False, encoding="utf-8")

    print("\n")
    logger.info("✅ Mapeamento doc → tópico salvo em:\n %s\n", output_path)


# =============================================================================
# API PÚBLICA
# =============================================================================
def generate_topics_from_documents(
    documents: list[str],
    df_docs: pd.DataFrame | None = None,
    output_csv: str | Path = "data/processed/topics_extracted.csv",
    output_mapping_csv: str | Path = "data/processed/topic_document_mapping.csv",
    embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
    min_cluster_size: int = 8,
    min_samples: int = 4,
    n_neighbors: int = 12,    
    reduction_strategy: ReductionStrategy = "similarity_threshold",
    reduction_nr_topics: int | None = None,
    reduction_max_distance: float = 0.55,
) -> pd.DataFrame:
    """
    Gera tópicos via BERTopic a partir de uma lista de abstracts.

    Parâmetros de clustering (min_cluster_size, min_samples, n_neighbors)
    controlam a granularidade dos tópicos. Os defaults favorecem tópicos
    mais amplos (macro), reduzindo micro-tópicos e juntando clusters muito pequenos.   

    Parâmetros de redução pós-clustering:
    - reduction_strategy: "none" (default, sem redução), "auto", "fixed"
      (requer reduction_nr_topics) ou "similarity_threshold" (usa
      reduction_max_distance).
 
    Retorna um DataFrame com o schema:
      Topic, Name, Num_Documents, Keywords, Keywords_RAW,
      Representative_Docs, Representative_Docs_JSON
    """
    print(f"\n{'='*60}")
    print("ETAPA 2: Agrupamento temático (BERTopic)")
    print(f"{'='*60}\n")
    
    logger.info("Agrupamento temático com BERTopic — %d documentos\n", len(documents))

    # Ajusta granularidade dinamicamente para subconjuntos de documentos por domínio
    actual_min_cluster_size = min_cluster_size
    actual_min_samples = min_samples
    if len(documents) < 300:
        actual_min_cluster_size = max(4, min(min_cluster_size, len(documents) // 35))
        actual_min_samples = max(2, min(min_samples, actual_min_cluster_size // 2))
        logger.info(
            "Subconjunto de domínio (%d docs): usando min_cluster_size=%d, min_samples=%d",
            len(documents), actual_min_cluster_size, actual_min_samples,
        )

    topic_model = _build_topic_model(
        actual_min_cluster_size, 
        actual_min_samples, 
        n_neighbors, 
        embedding_model_name,
    )
    topics, _probs = topic_model.fit_transform(documents)

    n_topics_before = len({t for t in topics if t != -1})
    logger.info("Tópicos antes da redução: %d", n_topics_before)

    topics = _reduce_topics(
        topic_model,
        documents,
        strategy=reduction_strategy,
        nr_topics=reduction_nr_topics,
        max_distance=reduction_max_distance,
    )

    n_topics_after = len({t for t in topics if t != -1})
    logger.info(
        "✅ Tópicos após redução (%s): %d → %d",
        reduction_strategy, n_topics_before, n_topics_after,
    )

    info = topic_model.get_topic_info()

    # Contagens por tópico (-1 = outliers)
    counts: Counter = Counter(int(t) for t in topics)

    # Salva mapeamento doc -> topico para permitir criar nos folha (papers/abstracts) no grafo.
    if df_docs is not None and len(df_docs) == len(topics):
        _save_topic_document_mapping(df_docs, topics, Path(output_mapping_csv))
    elif df_docs is not None:
        logger.warning(
            "docs_df tem %d linhas mas topics tem %d entradas — mapeamento não salvo.",
            len(df_docs), len(topics),
        )

    abstract_to_title = _build_abstract_to_title_lookup(df_docs)

    topics_data = [
        _build_topic_row(int(row["Topic"]), row, topic_model, counts, abstract_to_title)
        for _, row in info.iterrows()
        if int(row["Topic"]) != -1  # -1 = outliers não classificados pelo HDBSCAN
    ]

    df_topics = pd.DataFrame(topics_data).sort_values(["Num_Documents", "Topic"], ascending=[False, True])

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_topics.to_csv(output_path, index=False)

    logger.info("✅ %d tópicos salvos em:\n %s\n", len(df_topics), output_path)
    if not df_topics.empty:
        logger.debug(
            "\n%s",
            df_topics[["Topic", "Name", "Num_Documents"]].head(20).to_string(index=False),
        )

    return df_topics
