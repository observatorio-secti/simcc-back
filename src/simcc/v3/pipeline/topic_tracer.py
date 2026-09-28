"""
topic_tracer.py — Geração do CSV de rastreabilidade documento → subtópico.
 
Para cada documento no topic_document_mapping.csv, seleciona o subtópico mais relevante
do tópico ao qual pertence e gera um CSV de rastreabilidade, incluindo o pesquisador vinculado ao documento.
 
Não depende de grafo nem de embeddings — opera exclusivamente sobre DataFrames.
"""
from __future__ import annotations
 
import logging
import re
from pathlib import Path
 
import pandas as pd
import networkx as nx

from .topic_utils import merge_topic_rows, tokenize
from .constants import TAXONOMY_ORIGIN, TOPIC_ORIGIN

from .graph_utils import get_topic_areas
 
logger = logging.getLogger(__name__)


def _pick_best_subtopic(article_text: str, subtopics: list[dict]) -> dict | None:
    """
    Seleciona o subtópico mais relevante para um documento por sobreposição de tokens.
 
    Pontuação por token compartilhado:
    - nome do subtópico: peso 3 (mais específico)
    - keywords do subtópico: peso 2
    - sobreposição geral: peso 1
 
    Se o documento não tiver tokens válidos, retorna o primeiro subtópico da lista.
    """
    article_tokens = tokenize(article_text)
    if not article_tokens:
        return subtopics[0] if subtopics else None

    best_subtopic = None
    best_score = -1.0

    for sub in subtopics:
        subtopic_text = " ".join([sub["name"], *sub.get("keywords", [])])
        subtopic_tokens = tokenize(subtopic_text)
        overlap = len(article_tokens & subtopic_tokens)
        name_overlap = len(article_tokens & tokenize(sub["name"]))
        keyword_overlap = len(article_tokens & tokenize(" ".join(sub.get("keywords", []))))
        score = (name_overlap * 3) + (keyword_overlap * 2) + overlap

        if score > best_score:
            best_score = score
            best_subtopic = sub

    return best_subtopic or (subtopics[0] if subtopics else None)


def _deduplicate_trace_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rede de segurança contra duplicatas no CSV de rastreabilidade final —
    mesmo critério usado em document_repository._deduplicate_documents
    (pesquisador + título normalizado + ano), reaplicado aqui porque este
    CSV é o que o frontend consome diretamente.
    """
    if df.empty:
        return df

    def _normalize(value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip().lower())

    key = (
        df["researcher_name"].map(_normalize)
        + "|" + df["title"].map(_normalize)
        + "|" + df["year"].astype(str)
    )
    before = len(df)
    df = df.loc[~key.duplicated()].reset_index(drop=True)
    removed = before - len(df)
    if removed:
        logger.info("Removidas %d linhas duplicadas do CSV de rastreabilidade.", removed)
    return df


# =============================================================================
# API PÚBLICA
# =============================================================================
def build_topic_document_trace(
    mapping_csv: str | Path,
    topics_hierarchized_csv: str | Path,
    output_csv: str | Path,
    graph: nx.DiGraph,
) -> pd.DataFrame:
    """
    Gera um CSV de rastreabilidade de área → tópico → subtópico → documento → pesquisador.
 
    Para cada documento no mapping_csv, seleciona o subtópico mais relevante do
    tópico ao qual pertence usando sobreposição de tokens (_pick_best_subtopic).
 
    Colunas presentes no CSV de saída (além das do mapping original):
      - area_labels       : nome das áreas
      - topic_label       : nome consolidado do tópico
      - topic_coverage    : descrição do conteúdo do tópico
      - topic_group_size  : total de documentos no grupo
      - subtopic_label    : subtópico mais relevante para o documento
      - subtopic_keywords : keywords do subtópico selecionado
      - researcher_id     : ID do pesquisador vinculado ao documento
      - researcher_name   : nome do pesquisador (vem do JOIN no fetch_documents)
      - periodical_name   :
      - qualis            :
      - jcr               :
 
    Documentos sem tópico válido ou sem subtópico correspondente são ignorados.
    Documentos sem researcher_id ou researcher_name recebem string vazia nessas
    colunas — não são descartados, pois o conteúdo do documento ainda é válido.
    """
    print(f"\n{'='*60}")
    print("ETAPA 6: Construção do CSV de rastreabilidade documento → subtópico")
    print(f"{'='*60}\n")

    df_map = pd.read_csv(mapping_csv, encoding="utf-8")
    df_topics = pd.read_csv(topics_hierarchized_csv, encoding="utf-8")
    _merged_topics, topic_lookup = merge_topic_rows(df_topics)

    topic_areas = get_topic_areas(graph)

    trace_rows = []
    for _, row in df_map.iterrows():
        try:
            topic_id = int(row["Topic"])
        except (ValueError, KeyError):
            continue

        topic_meta = topic_lookup.get(topic_id)
        if not topic_meta:
            continue

        article_text = " ".join(
            str(row.get(col, "")).strip()
            for col in ["title", "abstract", "content"]
            if str(row.get(col, "")).strip()
        )
        best_subtopic = _pick_best_subtopic(article_text, topic_meta["subtopics"])
        if not best_subtopic:
            continue
    
        area_labels = "; ".join(topic_areas.get(topic_meta["topic_label"], []))

        trace_row = row.to_dict()
        trace_row["area_labels"] = area_labels
        trace_row["topic_label"] = topic_meta["topic_label"]
        trace_row["topic_coverage"] = topic_meta["coverage"]
        trace_row["topic_group_size"] = topic_meta["num_documents"]
        trace_row["subtopic_label"] = best_subtopic["name"]
        trace_row["subtopic_keywords"] = ", ".join(best_subtopic.get("keywords", []))
        
        # Campos presentes no topic_document_mapping
        trace_row["researcher_id"] = str(row.get("researcher_id", "") or "")
        trace_row["researcher_name"] = str(row.get("researcher_name", "") or "")

        trace_row["periodical_name"] = str(row.get("periodical_name", "") or "")
        trace_row["qualis"] = str(row.get("qualis", "") or "")
        trace_row["jcr"] = str(row.get("jcr", "") or "")        
        
        trace_rows.append(trace_row)

    df_trace = pd.DataFrame(trace_rows)
    df_trace = _deduplicate_trace_rows(df_trace)

    # Garante que as colunas estejam presentes mesmo se
    # nenhum documento trouxer esses campos (ex: fonte CSV sem JOIN).    
    for col in ("researcher_id", "researcher_name", "periodical_name", "qualis", "jcr"):
        if col not in df_trace.columns:
            df_trace[col] = ""

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_trace.to_csv(output_path, index=False, encoding="utf-8")

    logger.info("✅ CSV de %d linhas salvo em:\n %s", len(df_trace), output_path)
    return df_trace