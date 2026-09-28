"""
graph_utils.py — Funções puras de lógica de negócio sobre grafos NetworkX.

Este módulo contém exclusivamente funções que operam sobre nx.DiGraph e não
possuem nenhuma dependência de interface gráfica (Streamlit, Pyvis etc.).
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path

import networkx as nx

from .constants import TAXONOMY_ORIGIN, TOPIC_ORIGIN, SUBTOPIC_ORIGIN

logger = logging.getLogger(__name__)


# =============================================================================
# CONSULTA E FILTRAGEM DO GRAFO
# =============================================================================
def get_available_areas(graph: nx.DiGraph, area_layer: int = 1) -> list[str]:
    """
    Retorna os nós do nível de filtragem da taxonomia presentes no grafo.

    Por padrão, usa layer=1 (equivalente a "Grande Área" no CNPq).
    Para outras taxonomias, passe o area_filter_layer do TaxonomyConfig.

    A lista é ordenada alfabeticamente para exibição consistente na UI.
    """
    return sorted(
        node
        for node, attrs in graph.nodes(data=True)
        if attrs.get("origin") == TAXONOMY_ORIGIN and attrs.get("layer") == area_layer
    )

def get_topic_nodes(graph: nx.DiGraph) -> list[str]:
    """
    Retorna o conjunto de nós que representam tópicos gerados pelo pipeline.

    Útil para filtrar apenas os nós relevantes para análise de tópicos,
    ignorando áreas, subáreas e subtópicos.
    """    
    return [
        node 
        for node, attrs in graph.nodes(data=True)
        if attrs.get("origin") == TOPIC_ORIGIN
    ]


def get_topic_areas(graph: nx.DiGraph) -> dict[str, list[str]]:
    """
    Para cada nó do tipo tópico no grafo, retorna as áreas (ancestrais
    de layer 1) associadas a ele.

    Retorna um dicionário topic_label -> lista de area_labels.
    """
    topic_areas: dict[str, list[str]] = {}
    topic_nodes = get_topic_nodes(graph)

    for topic_node in topic_nodes:
        topic_label = graph.nodes[topic_node]["label"]
        areas = {
            graph.nodes[ancestor]["label"]
            for ancestor in nx.ancestors(graph, topic_node)
            if graph.nodes[ancestor].get("origin") == TAXONOMY_ORIGIN
            and graph.nodes[ancestor].get("layer") == 1
        }
        topic_areas[topic_label] = sorted(areas)

    return topic_areas


def get_areas_with_topics(graph: nx.DiGraph) -> list[str]:
    """
    Retorna apenas as áreas que têm ao menos um tópico
    conectado em sua subárvore — usadas como default do filtro na UI.
    """
    topic_nodes = {
        node 
        for node, attrs in graph.nodes(data=True)
        if attrs.get("origin") == TOPIC_ORIGIN
    }
    
    areas_with_topics = []
    for area in get_available_areas(graph):
        descendants = nx.descendants(graph, area)
        if descendants & topic_nodes:
            areas_with_topics.append(area)

    return areas_with_topics


def get_tree_by_area(graph: nx.DiGraph, selected_areas: list[str]) -> nx.DiGraph | None:
    """
    Extrai um subgrafo contendo as áreas selecionadas e toda a sua vizinhança.

    Para cada área selecionada, inclui:
    - o próprio nó da área
    - todos os seus descendentes (subáreas, especialidades, tópicos)
    """
    nodes_to_keep: set[str] = set()

    for area in selected_areas:
        if area not in graph:
            continue
        nodes_to_keep.add(area)
        nodes_to_keep.update(nx.descendants(graph, area))

    if not nodes_to_keep:
        return None

    return graph.subgraph(nodes_to_keep).copy()


def get_taxonomy_root(graph: nx.DiGraph) -> str | None:
    """
    Retorna o nó raiz da taxonomia (layer=0), ou None se não existir.
    É o único nó que é ancestral de todos os outros — adicionado explicitamente
    na visualização por não pertencer a nenhuma área específica.
    """
    return next(
        (
            node 
            for node, attrs in graph.nodes(data=True)
            if attrs.get("origin") == TAXONOMY_ORIGIN and attrs.get("layer") == 0
        ),
        None,
    )


def _add_relevant_descendants(
    graph: nx.DiGraph, 
    node: str, 
    relevant_nodes: set[str]
) -> None:
    """
    Adiciona ao conjunto `relevant_nodes` os subtópicos descendentes de `node`.
    Auxiliar de `get_relevant_nodes`, separada para manter a função principal legível.
    """
    try:
        for descendant in nx.descendants(graph, node):
            origin = str(graph.nodes[descendant].get("origin", "")).upper()
            if origin == SUBTOPIC_ORIGIN:
                relevant_nodes.add(descendant)
    except Exception:
        logger.warning("Falha ao calcular descendentes do nó %s", node, exc_info=True)


def get_relevant_nodes(
    graph: nx.DiGraph, 
    selected_areas: list[str], 
    show_full_tree: bool, 
    show_isolated: bool
) -> set[str]:
    """
    Calcula o conjunto de nós que devem ser exibidos para as áreas selecionadas.

    Dois eixos independentes controlam o resultado:

    show_full_tree — controla quais nós da área são exibidos:
        True  → inclui todos os nós da subárvore selecionada, mesmo os que
                não têm nenhum tópico associado (ramos vazios visíveis).
        False → inclui apenas os nós que fazem parte do caminho até
                algum tópico (ancestrais de tópicos dentro da área).

    show_isolated — controla quais tópicos são incluídos:
        True  → inclui todos os tópicos do grafo, mesmo os que não têm
                nenhum ancestral dentro da área selecionada. Útil para
                depuração e visão geral do pipeline.
        False → inclui apenas os tópicos que têm ao menos um ancestral
                dentro da área selecionada.

    Em ambos os casos, os subtópicos de cada tópico incluído
    também são adicionados via _add_relevant_descendants.
    """
    # Subgrafo das áreas selecionadas
    graph_area = get_tree_by_area(graph, selected_areas)
    if graph_area is None:
        return set()

    area_nodes = set(graph_area.nodes())
    relevant_nodes = set(area_nodes) if show_full_tree else set()

    # O nó raiz é sempre incluído quando existe
    taxonomy_root = get_taxonomy_root(graph)
    if taxonomy_root is not None:
        relevant_nodes.add(taxonomy_root)

    for node, attrs in graph.nodes(data=True):
        origin = str(attrs.get("origin", "")).upper()

        # Interessa apenas nós gerados pelo pipeline (tópicos BERTopic).
        if origin != TOPIC_ORIGIN:
            continue

        # Verifica se o tópico tem ao menos um ancestral na área selecionada.
        try:
            ancestors = nx.ancestors(graph, node)
        except Exception:
            logger.warning("Falha ao calcular ancestrais do nó %s", node, exc_info=True)
            ancestors = set()

        in_area = bool(ancestors & area_nodes)

        if not show_isolated and not in_area:
            continue

        relevant_nodes.add(node)
        _add_relevant_descendants(graph, node, relevant_nodes)

        # Inclui apenas os ancestrais dentro da área selecionada — garante
        # conectividade dos nós que levam a tópicos da área sem puxar
        # a hierarquia inteira de áreas externas (ex: tópico isolado de
        # Biologia não traz os nós de Biologia quando a área selecionada
        # é Matemática).
        relevant_nodes.update(ancestors & area_nodes)        

    return relevant_nodes


# =============================================================================
# SALVAMENTO DE GRAFOS EM DISCO
# =============================================================================
def save_base_graph(graph: nx.DiGraph, path: Path) -> None:
    """Persiste o grafo NetworkX em disco no formato pickle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(graph, f)
    logger.info(
        "✅ Grafo com %d nós e %d arestas salvo em:\n %s",
        graph.number_of_nodes(), graph.number_of_edges(), path,
    )

def save_final_graph(graph: nx.DiGraph, output_path: str | Path) -> None:
    """Serializa o grafo NetworkX em disco no formato pickle."""
    print(f"\n{'='*60}")
    print("ETAPA 5: Salvamento do grafo")
    print(f"{'='*60}\n")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(graph, f)

    logger.info("✅ Grafo salvo em:\n %s\n", output_path)


# =============================================================================
# Carregamento do grafo
# =============================================================================
def load_graph(path: Path) -> nx.DiGraph:
    """Carrega um grafo NetworkX serializado em .gpickle."""
    if not path.exists():
        raise FileNotFoundError(f"Grafo não encontrado: {path}")
    with path.open("rb") as f:
        graph: nx.DiGraph = pickle.load(f)
    logger.info("Grafo carregado: %d nós | %d arestas", graph.number_of_nodes(), graph.number_of_edges())
    return graph