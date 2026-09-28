"""
topic_utils.py — Utilitários compartilhados entre topic_tracer e graph_builder.
 
Funções de texto e de mesclagem de tópicos usadas por ambos os módulos.
Separadas aqui para evitar duplicação sem criar dependências cruzadas.
"""
from __future__ import annotations
 
import json
import logging
import re
 
import pandas as pd
 
logger = logging.getLogger(__name__)


# =============================================================================
# UTILITÁRIOS DE TEXTO
# =============================================================================
def _safe_json_loads(raw_value: object, default: object) -> object:
    """Desserializa JSON de forma segura, retornando `default` em caso de falha."""
    if not isinstance(raw_value, str) or not raw_value.strip():
        return default
    try:
        return json.loads(raw_value)
    except Exception:
        return default


def _normalize_name(value: str) -> str:
    """Normaliza um nome para uso como chave: lowercase, sem espaços duplos."""
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def tokenize(value: str) -> set[str]:
    """
    Extrai tokens de uma string para comparação por sobreposição.
    Considera apenas tokens com 3+ caracteres, incluindo acentuados.
    """
    return set(re.findall(r"\b[\wÀ-ÿ\-]{3,}\b", str(value or "").lower()))


# =============================================================================
# NORMALIZAÇÃO DE TÓPICOS
# =============================================================================
def _normalize_subtopics(row: pd.Series) -> list[dict]:
    """
    Extrai e normaliza os assuntos (subtópicos) de uma linha do CSV hierarquizado.
 
    Tenta ler a coluna 'Subtopics' como JSON estruturado. Se estiver vazia ou
    malformada, usa as keywords brutas do BERTopic como fallback — garantindo
    que todo tópico tenha ao menos um assunto para entrar no grafo.
    """
    raw_subtopics = _safe_json_loads(row.get("Subtopics", "[]"), [])
    normalized = []

    for idx, subtopic in enumerate(raw_subtopics[:6]):
        if isinstance(subtopic, dict):
            name = str(subtopic.get("name", "")).strip()
            keywords = [str(k).strip() for k in subtopic.get("keywords", []) if str(k).strip()]
            frequency = int(subtopic.get("frequency", 1) or 1)
        else:
            name = str(subtopic).strip()
            keywords = []
            frequency = 1

        if not name:
            continue

        normalized.append(
            {
                "idx": idx,
                "name": name,
                "keywords": keywords,
                "frequency": frequency,
            }
        )

    # Fallback controlado: usa keywords do tópico apenas se nada estruturado vier do LLM.
    if normalized:
        return normalized

    fallback_keywords = [
        kw.strip()
        for kw in str(row.get("Keywords", "")).split(",")
        if kw.strip()
    ]
    for idx, keyword in enumerate(fallback_keywords[:5]):
        normalized.append(
            {
                "idx": idx,
                "name": keyword,
                "keywords": [keyword],
                "frequency": 1,
            }
        )
    return normalized


def _merge_subtopic(merged_subtopics: dict, sub: dict) -> None:
    """Mescla um subtópico no dicionário acumulador, somando frequência e deduplicando keywords."""
    sub_key = _normalize_name(sub["name"])
    if not sub_key:
        return

    merged_sub = merged_subtopics.setdefault(
        sub_key,
        {"idx": len(merged_subtopics), "name": sub["name"], "keywords": [], "frequency": 0},
    )
    merged_sub["frequency"] += int(sub.get("frequency", 1) or 1)
    for keyword in sub.get("keywords", []):
        if keyword and keyword not in merged_sub["keywords"]:
            merged_sub["keywords"].append(keyword)


def _accumulate_row(merged_topics: dict, row: pd.Series) -> dict | None:
    """
    Acumula uma linha do CSV no dicionário de tópicos mesclados.
    Retorna o dict do tópico atualizado, ou None se a linha for inválida.
    """
    topic_id = int(row["Topic"])
    if topic_id == -1:
        return None

    topic_label = str(row.get("Area", "")).strip()
    if not topic_label:
        return None

    subtopics = _normalize_subtopics(row)
    if not subtopics:
        return None

    topic_key = _normalize_name(topic_label)
    merged = merged_topics.setdefault(
        topic_key,
        {
            "topic_key": topic_key,
            "topic_label": topic_label,
            "topic_ids": [],
            "main_areas": [],
            "coverage_parts": [],
            "num_documents": 0,
            "subtopics": {},
            "relevance_flags": [],
        },
    )

    merged["topic_ids"].append(topic_id)
    merged["num_documents"] += int(row.get("Num_Documents", 0) or 0)
    merged["relevance_flags"].append(bool(row.get("Is_Relevant", True)))

    coverage = str(row.get("Coverage", "")).strip()
    if coverage and coverage not in merged["coverage_parts"]:
        merged["coverage_parts"].append(coverage)

    main_areas = _safe_json_loads(row.get("Main_Areas", "[]"), [])
    if main_areas:
        merged["main_areas"].extend(main_areas)

    for sub in subtopics:
        _merge_subtopic(merged["subtopics"], sub)

    return merged


def _build_merged_list(merged_topics: dict) -> tuple[list[dict], dict[int, dict]]:
    """
    Constrói a lista final de tópicos mesclados e o lookup completo topic_id → metadados.
    """
    merged_list = []
    topic_lookup: dict[int, dict] = {}

    for topic_key, merged in merged_topics.items():
        subtopics = sorted(
            merged["subtopics"].values(),
            key=lambda item: (-item["frequency"], item["name"].lower()),
        )
        for idx, sub in enumerate(subtopics):
            sub["idx"] = idx

        is_relevant = any(merged["relevance_flags"]) if merged["relevance_flags"] else True

        merged_topic = {            
            "topic_label": merged["topic_label"],            
            "main_areas": merged["main_areas"],
            "coverage": " | ".join(merged["coverage_parts"][:3]),
            "num_documents": merged["num_documents"],
            "subtopics": subtopics,
            "is_relevant": is_relevant,
        }
        merged_list.append(merged_topic)

        for topic_id in merged["topic_ids"]:
            topic_lookup[topic_id] = {
                "topic_key": topic_key,
                "topic_label": merged["topic_label"],
                "subtopics": subtopics,
                "coverage": merged_topic["coverage"],
                "num_documents": merged["num_documents"],
                "is_relevant": is_relevant,
            }

    return merged_list, topic_lookup


def merge_topic_rows(df_topics_hierarchized: pd.DataFrame) -> tuple[list[dict], dict[int, dict]]:
    """
    Mescla linhas do CSV que representam o mesmo tópico (mesmo nome de área).
 
    O BERTopic pode gerar múltiplos IDs numéricos para tópicos semanticamente
    equivalentes. Esta função os consolida em um único nó, somando contagens
    e deduplicando assuntos por nome normalizado.
    """
    merged_topics: dict[str, dict] = {}

    for _, row in df_topics_hierarchized.iterrows():
        _accumulate_row(merged_topics, row)

    return _build_merged_list(merged_topics)