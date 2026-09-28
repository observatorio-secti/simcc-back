"""
simcc/services/classifier_taxonomy_service.py

Responsabilidades:
  - Carregar o grafo NetworkX do disco (.gpickle)
  - Converter NetworkX DiGraph → GraphResponse (formato Cytoscape/vis.js)
  - Listar taxonomias disponíveis a partir dos arquivos em disco
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Iterator

import networkx as nx

from simcc.core.settings import Settings
from simcc.schemas_classifier.taxonomy import (
    GraphElement,
    EdgeData,
    EdgeElement,
    GraphResponse,
    GraphSummary,
    NodeData,
    NodeElement,
    TaxonomyItem, 
    TaxonomyListResponse
)
from simcc.pipeline.graph_utils import get_areas_with_topics, get_relevant_nodes, load_graph

logger = logging.getLogger(__name__)


def _slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def _node_to_element(node_id: str, attrs: dict) -> NodeElement:
    data = NodeData(
        id=node_id,
        label=attrs.get("label", node_id),
        origin=attrs.get("origin", "TAXONOMY"),
        layer=attrs.get("layer", 0),        
        color=attrs.get("color", "#97C2FC"),     
        size=attrs.get("size"),
        num_documents=attrs.get("num_documents"),
        coverage=attrs.get("coverage"),        
    )
    return NodeElement(data=data)


def _edge_to_element(edge_id: str, source: str, target: str, attrs: dict) -> EdgeElement:
    data = EdgeData(
        id=edge_id,
        source=source,
        target=target,
        relation=attrs.get("relation", ""),
        weight=attrs.get("weight", 1.0),
        similarity_score=attrs.get("similarity_score"),
    )
    return EdgeElement(data=data)


def graph_to_elements(graph: nx.DiGraph) -> Iterator[GraphElement]:
    for node_id, attrs in graph.nodes(data=True):
        yield _node_to_element(str(node_id), attrs)

    for i, (source, target, attrs) in enumerate(graph.edges(data=True)):
        edge_id = attrs.get("id", f"e{i}")
        yield _edge_to_element(str(edge_id), str(source), str(target), attrs)


def build_graph_response(graph: nx.DiGraph, taxonomy_name: str) -> GraphResponse:
    elements = list(graph_to_elements(graph))

    origin_counter: Counter[str] = Counter()
    for el in elements:
        if isinstance(el, NodeElement):
            origin_counter[el.data.origin] += 1

    summary = GraphSummary(
        total_nodes=graph.number_of_nodes(),
        total_edges=graph.number_of_edges(),
        nodes_by_origin=dict(origin_counter),
    )

    return GraphResponse(
        taxonomy_name=taxonomy_name,
        elements=elements,
        summary=summary,
    )


def filter_graph(
    graph: nx.DiGraph,
    origins: list[str] | None = None,
    min_layer: int | None = None,
    max_layer: int | None = None,
) -> nx.DiGraph:
    if not origins and min_layer is None and max_layer is None:
        return graph

    def node_matches(attrs: dict) -> bool:
        if origins and attrs.get("origin") not in origins:
            return False
        layer = attrs.get("layer", 0)
        if min_layer is not None and layer < min_layer:
            return False
        if max_layer is not None and layer > max_layer:
            return False
        return True

    matching_nodes = [n for n, a in graph.nodes(data=True) if node_matches(a)]
    return graph.subgraph(matching_nodes).copy()


def list_taxonomies(settings: Settings) -> TaxonomyListResponse:
    taxonomies_dir = settings.taxonomies_dir
    processed_dir = settings.processed_dir

    items: list[TaxonomyItem] = []
    seen: set[str] = set()

    # 1. Procurar taxonomias processadas (.gpickle)
    if processed_dir.exists():
        for graph_file in sorted(processed_dir.glob("*_final_graph.gpickle")):
            slug_name = graph_file.stem.replace("_final_graph", "")
            taxonomy_name = slug_name.upper()
            total_nodes = 0        
            domain_description: str | None = None

            try:
                g = load_graph(graph_file)
                total_nodes = g.number_of_nodes()
            except Exception:
                pass

            config_path = taxonomies_dir / f"{slug_name}_config.json"
            if config_path.exists():
                try:
                    config_data = json.loads(config_path.read_text(encoding="utf-8"))
                    domain_description = config_data.get("domain_description")
                except Exception:
                    pass

            items.append(
                TaxonomyItem(
                    taxonomy_name=taxonomy_name, 
                    total_nodes=total_nodes, 
                    domain_description=domain_description
                )
            )
            seen.add(slug_name)

    # 2. Adicionar taxonomias geradas ou base que ainda não tem final_graph
    if taxonomies_dir.exists():
        for json_file in sorted(taxonomies_dir.glob("*_taxonomy.json")):
            slug_name = json_file.stem.replace("_taxonomy", "")
            if slug_name in seen:
                continue
            taxonomy_name = slug_name.upper()
            domain_description = None
            config_path = taxonomies_dir / f"{slug_name}_config.json"
            if config_path.exists():
                try:
                    config_data = json.loads(config_path.read_text(encoding="utf-8"))
                    domain_description = config_data.get("domain_description")
                    taxonomy_name = config_data.get("name", taxonomy_name)
                except Exception:
                    pass

            items.append(
                TaxonomyItem(
                    taxonomy_name=taxonomy_name,
                    total_nodes=0,
                    domain_description=domain_description,
                )
            )

    return TaxonomyListResponse(items=items, total=len(items))


def get_taxonomy_graph(
    settings: Settings,
    taxonomy_name: str,
    origins: list[str] | None = None,
    min_layer: int | None = None,
    max_layer: int | None = None,
) -> GraphResponse:
    slug_name = _slug(taxonomy_name)
    processed_dir = settings.processed_dir
    taxonomies_dir = settings.taxonomies_dir

    final_graph_path = processed_dir / f"{slug_name}_final_graph.gpickle"
    base_graph_path = processed_dir / f"{slug_name}_base_graph.gpickle"

    if final_graph_path.exists():
        graph = load_graph(final_graph_path)
    elif base_graph_path.exists():
        graph = load_graph(base_graph_path)
    else:
        # Fallback: construir grafo simples a partir do JSON da taxonomia
        taxonomy_json_path = taxonomies_dir / f"{slug_name}_taxonomy.json"
        if not taxonomy_json_path.exists():
            raise FileNotFoundError(f"Taxonomia '{taxonomy_name}' não encontrada.")
        
        tree = json.loads(taxonomy_json_path.read_text(encoding="utf-8"))
        if isinstance(tree, list):
            tree = {"name": taxonomy_name.upper(), "children": tree}
        
        graph = nx.DiGraph()
        def visit(item: dict, layer: int, parent_id: str | None):
            label = str(item.get("name", ""))
            node_id = f"{_slug(label)}_{layer}"
            graph.add_node(node_id, label=label, origin="TAXONOMY", layer=layer, color="#97C2FC")
            if parent_id:
                graph.add_edge(parent_id, node_id, relation="CHILD_OF", weight=1.0)
            for child in item.get("children", []):
                visit(child, layer + 1, node_id)
        
        visit(tree, 0, None)

    if origins or min_layer is not None or max_layer is not None:
        graph = filter_graph(graph, origins, min_layer, max_layer)

    return build_graph_response(graph, taxonomy_name.upper())
