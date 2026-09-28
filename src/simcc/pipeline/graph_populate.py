"""
graph_populate.py — Constrói e persiste o grafo base de uma taxonomia hierárquica.

O grafo base contém apenas os nós da taxonomia, sem tópicos nem artigos.
Ele serve como estrutura hierárquica sobre a qual o pipeline adiciona os
tópicos gerados posteriormente.
"""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path

import networkx as nx

from .taxonomy_config import TaxonomyConfig
from .graph_utils import save_base_graph
 
logger = logging.getLogger(__name__)


# =============================================================================
# CONSTRUÇÃO DO GRAFO
# =============================================================================
def _recursive_graph_populate(
    graph: nx.DiGraph, 
    node: dict,
    taxonomy_config: TaxonomyConfig,
    layer: int = 0
) -> str:
    """
    Insere recursivamente um nó e seus filhos no grafo.
 
    Atributos visuais (cor, tamanho) e semânticos (origin)
    vêm do TaxonomyConfig — sem hardcode de domínio específico.
    Retorna o nome do nó inserido, usado pelo chamador para criar a aresta pai → filho.
    """
    name = node["name"]    
    size = max(10, 25 - (layer * 5)) # Tamanho proporcional ao nível

    graph.add_node(
        name,
        label=name,        
        origin=taxonomy_config.origin_label,        
        layer=layer,
        color=taxonomy_config.node_color,
        size=size,
    )

    for child in node.get("children", []):
        child_name = _recursive_graph_populate(graph, child, taxonomy_config, layer + 1)
        graph.add_edge(name, child_name, relation="CHILD_OF")

    return name


def _build_base_graph(taxonomy_data: dict | list, taxonomy_config: TaxonomyConfig) -> nx.DiGraph:
    """
    Constrói o grafo a partir dos dados da taxonomia e de um TaxonomyConfig.
 
    Suporta dois formatos de entrada:
    - dict: taxonomia com um único nó raiz explícito no JSON
    - list: múltiplos nós de nível 1, agrupados sob um nó raiz sintético
    """
    graph = nx.DiGraph(name=f"Taxonomia {taxonomy_config.name} Base")
 
    if isinstance(taxonomy_data, dict):
        _recursive_graph_populate(graph, taxonomy_data, taxonomy_config, layer=0)
 
    elif isinstance(taxonomy_data, list):        
        graph.add_node(
            "TAXONOMY_ROOT",
            label=taxonomy_config.name,            
            origin=taxonomy_config.origin_label,            
            layer=0,            
            color=taxonomy_config.node_color,
            size=25,
        )
        for item in taxonomy_data:
            child_name = _recursive_graph_populate(graph, item, taxonomy_config, layer=1)
            graph.add_edge("TAXONOMY_ROOT", child_name, relation="CHILD_OF")
 
    return graph


def _extract_subgraph(graph: nx.DiGraph, root: str):    
    """
    Extrai um subgrafo de uma taxonomia base, a partir de um nó raiz.
    Inclui todos os seus descendentes e todos os seus ancestrais.

    Esta função é projetada para ser usada no grafo base, antes da adição de tópicos.
    """
    if root not in graph:
        logger.warning("Nó raiz '%s' não encontrado no grafo — subgrafo não gerado.", root)
        return None
 
    relevant_nodes = {root}
    relevant_nodes.update(nx.descendants(graph, root))
    relevant_nodes.update(nx.ancestors(graph, root))

    return graph.subgraph(relevant_nodes).copy()


# =============================================================================
# API PÚBLICA
# =============================================================================
def build_and_save_base_graph(
    base_graph_path: Path,
    taxonomy_structure: dict | list,
    taxonomy_config: TaxonomyConfig,
) -> nx.DiGraph:
    """
    Constrói o grafo base da taxonomia e o persiste em disco.
    """
    print(f"\n{'='*60}")
    print("Construção do grafo base")
    print(f"{'='*60}\n")

    logger.info("Construindo grafo base — taxonomia: %s", taxonomy_config.name)

    graph = _build_base_graph(taxonomy_structure, taxonomy_config)
    save_base_graph(graph, base_graph_path)

    return graph
