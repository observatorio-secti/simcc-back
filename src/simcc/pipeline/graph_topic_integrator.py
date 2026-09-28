"""
graph_topic_integrator.py — Integração de tópicos no grafo de taxonomia.

Recebe o grafo base da taxonomia e os tópicos hierarquizados pelo LLM
e insere nós TOPIC e SUBTOPIC posicionados semanticamente nos nós mais similares da taxonomia.

Decisões de design deste módulo:    
- não cria nós de artigos no grafo (rastreabilidade fica em topic_tracer.py)
- só injeta tópicos que tenham ao menos um assunto explícito
- tópicos com o mesmo nome são mesclados em um único nó
- o parâmetro `model` é injetável para evitar recarregar embeddings em testes
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Iterable

import numpy as np
import networkx as nx
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from .constants import TAXONOMY_ORIGIN, SUBTOPIC_ORIGIN, TOPIC_ORIGIN
from .embeddings import DEFAULT_EMBEDDING_MODEL, get_embedding_model
from .topic_utils import merge_topic_rows

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES VISUAIS
# =============================================================================
TOPIC_COLOR = "#FFD54F"
SUBTOPIC_COLOR = "#FFB74D"
TOPIC_NODE_SIZE = 18
SUBTOPIC_NODE_SIZE = 12


# =============================================================================
# UTILITÁRIOS DE GRAFO
# =============================================================================
def _node_path(graph: nx.DiGraph, node: str) -> str:
    """
    Constrói o caminho hierárquico de um nó da taxonomia como string legível.
    Exemplo: 'Ciências Exatas e da Terra > Física > Física da Matéria Condensada'
    Usado para gerar embeddings mais ricos para a ancoragem semântica.
    """
    try:
        ancestors = [a for a in nx.ancestors(graph, node) if graph.nodes[a].get("origin") == TAXONOMY_ORIGIN]
        ancestors = sorted(ancestors, key=lambda n: graph.nodes[n].get("layer", 0))
        parts = [graph.nodes[a].get("label", a) for a in ancestors if graph.nodes[a].get("layer", 0) > 0]
        parts.append(graph.nodes[node].get("label", node))
        return " > ".join(parts)
    except Exception:
        logger.warning("Falha ao construir caminho do nó %s", node, exc_info=True)
        return graph.nodes[node].get("label", node)


def _candidate_parents(graph: nx.DiGraph) -> list[str]:
    """
    Retorna todos os nós da taxonomia base — candidatos a receber tópicos.
    """ 
    return [
        n for n, attr in graph.nodes(data=True)
        if attr.get("origin") == TAXONOMY_ORIGIN
    ]


def _candidate_ancestors(graph: nx.DiGraph, nodes: Iterable[str]) -> list[set[str]]:
    """
    Retorna a lista de conjuntos de ancestrais para cada nó informado.
    Falhas de traversal resultam em conjunto vazio e são logadas como warning.
    """
    ancestors_list = []
    for node in nodes:
        try:
            ancestors_list.append(nx.ancestors(graph, node))
        except Exception:
            logger.warning("Falha ao calcular ancestrais do nó %s", node, exc_info=True)
            ancestors_list.append(set())
    return ancestors_list


def _pick_parent_index(
    similarities: np.ndarray,
    candidate_parents: list[str],
    candidate_ancestors: list[set[str]],
    primary_area: str | None,
) -> int:
    """
    Escolhe o índice do nó pai mais adequado para um tópico.
 
    Se `primary_area` for fornecida (sugestão do LLM), prioriza candidatos
    cujos ancestrais contenham essa área. Entre os candidatos filtrados,
    escolhe o de maior similaridade semântica.
    Se nenhum candidato corresponder à área sugerida, usa a maior similaridade.
    """
    anchor = str(primary_area or "").strip()
    if anchor:
        anchored = [
            idx for idx, ancestors in enumerate(candidate_ancestors)
            if anchor in ancestors or candidate_parents[idx] == anchor
        ]
        if anchored:
            return max(anchored, key=lambda idx: similarities[idx])
    return int(similarities.argmax())


def _pick_primary_area(main_areas: list) -> str | None:
    """
    Extrai o nome da área mais relevante sugerida pelo LLM.
    Aceita tanto o campo 'area' quanto 'area_name' para compatibilidade
    com diferentes versões do schema de saída do topic_hierarchizer.
    """
    for area in main_areas:
        if isinstance(area, dict):
            label = str(area.get("area", "") or area.get("area_name", "")).strip()
            if label:
                return label
    return None


# =============================================================================
# CONSTRUÇÃO DE NÓS DO GRAFO
# =============================================================================
def _build_topic_node_attrs(
    topic_label: str,
    num_documents: int,
    coverage: str,
    parent_layer: int,    
) -> dict:
    """Constrói o dicionário de atributos de um nó TOPIC para o grafo."""
    return {
        "label": topic_label,        
        "origin": TOPIC_ORIGIN,        
        "color": TOPIC_COLOR,
        "size": TOPIC_NODE_SIZE,
        "layer": parent_layer + 1,        
        "num_documents": num_documents,
        "coverage": coverage,
    }


def _build_subtopic_node_attrs(
    sub_name: str,    
    topic_layer: int,    
) -> dict:
    """Constrói o dicionário de atributos de um nó SUBTOPIC para o grafo."""    
    return {
        "label": sub_name,        
        "origin": SUBTOPIC_ORIGIN,        
        "color": SUBTOPIC_COLOR,
        "size": SUBTOPIC_NODE_SIZE,
        "layer": topic_layer + 1,        
    }


# =============================================================================
# API PÚBLICA
# =============================================================================
def add_topics_to_graph(
    graph: nx.DiGraph,
    df_topics_hierarchized: pd.DataFrame,    
    embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> nx.DiGraph:
    """
    Insere tópicos e assuntos no grafo de taxonomia.
 
    Para cada tópico mesclado:
    1. Calcula a similaridade semântica com os nós folha da taxonomia.
    2. Escolhe o nó pai mais adequado (semântica + sugestão do LLM).
    3. Insere o nó TOPIC e suas arestas.
    4. Insere os nós SUBTOPIC filhos e suas arestas.
 
    O modelo de embeddings vem do cache de `embeddings.get_embedding_model`,
    evitando baixar/ instanciar os pesos a cada execução.
    """
    print(f"\n{'='*60}")
    print("ETAPA 4: Integração dos tópicos no grafo base")
    print(f"{'='*60}\n")

    embedding_model = get_embedding_model(embedding_model_name)
    
    candidate_parents = _candidate_parents(graph)
    candidate_paths = [_node_path(graph, node) for node in candidate_parents]
    taxonomy_embeddings = embedding_model.encode(candidate_paths)
    candidate_ancestors = _candidate_ancestors(graph, candidate_parents)
    merged_topics, _topic_lookup = merge_topic_rows(df_topics_hierarchized)

    inserted_topics = 0
    inserted_subtopics = 0
    skipped_irrelevant = 0

    for merged_topic in merged_topics:
        topic_label = merged_topic["topic_label"]

        if not merged_topic.get("is_relevant", True):
            skipped_irrelevant += 1
            logger.info(
                "Tópico '%s' marcado como não relevante para esta taxonomia — "
                "não integrado ao grafo.", topic_label,
            )
            continue

        confidence = float(merged_topic.get("confidence", 1.0) or 0.0)
        primary_area = _pick_primary_area(merged_topic["main_areas"])
        if confidence < 0.60 and not primary_area:
            skipped_irrelevant += 1
            logger.info(
                "Tópico '%s' possui baixa confiança (%.2f < 0.60) e sem área principal — "
                "não integrado ao grafo.", topic_label, confidence,
            )
            continue

        subtopics = merged_topic["subtopics"]
        coverage = merged_topic["coverage"]
        num_documents = merged_topic["num_documents"]
        
        # Monta query combinando label, cobertura e top-3 assuntos para embedding mais rico
        search_terms = [topic_label, coverage]
        search_terms.extend(sub["name"] for sub in subtopics[:3])
        query = " ".join(term for term in search_terms if term)
        query_embedding = embedding_model.encode([query])        
        similarities = cosine_similarity(query_embedding, taxonomy_embeddings)[0]

        parent_idx = _pick_parent_index(similarities, candidate_parents, candidate_ancestors, primary_area)
        parent_sim = float(similarities[parent_idx])

        # Se a similaridade com o pai escolhido for excessivamente baixa e não houver ancoragem forte
        if parent_sim < 0.25 and not primary_area:
            skipped_irrelevant += 1
            logger.info(
                "Tópico '%s' similaridade com nó pai muito baixa (%.3f < 0.25) — "
                "não integrado ao grafo.", topic_label, parent_sim,
            )
            continue

        parent_node = candidate_parents[parent_idx]
        topic_node = f"TOPIC::{topic_label}"

        if topic_node not in graph:
            parent_layer = graph.nodes[parent_node].get("layer", 2)
            graph.add_node(
                topic_node,
                **_build_topic_node_attrs(
                    topic_label, num_documents, coverage, parent_layer
                ),                
            )
            inserted_topics += 1
        else:
            # Atualiza metadados se o nó já existe (tópico duplicado mesclado)            
            graph.nodes[topic_node]["num_documents"] = num_documents
            graph.nodes[topic_node]["coverage"] = coverage

        if not graph.has_edge(parent_node, topic_node):
            graph.add_edge(
                parent_node,
                topic_node,
                relation="CHILD_OF",
                weight=1.0,
                similarity_score=round(float(similarities[parent_idx]), 3),
            )

        topic_layer = graph.nodes[topic_node].get("layer", 3)
        for sub in subtopics:
            subtopic_node = f"SUBTOPIC::{topic_label}::{sub['name']}"
            if subtopic_node not in graph:                
                graph.add_node(
                    subtopic_node,
                    **_build_subtopic_node_attrs(
                        sub["name"], topic_layer
                    ),
                )
                inserted_subtopics += 1

            if not graph.has_edge(topic_node, subtopic_node):
                graph.add_edge(topic_node, subtopic_node, relation="CHILD_OF", weight=1.0)

    print("\n")
    logger.info("✅ Tópicos híbridos inseridos: %d", inserted_topics)
    logger.info("✅ Assuntos inseridos: %d", inserted_subtopics)
    logger.info("⛔ Tópicos ignorados por não relevância à taxonomia: %d", skipped_irrelevant)
    return graph
