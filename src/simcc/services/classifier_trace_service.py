"""
simcc/services/classifier_trace_service.py — Leitura e transformação do CSV de rastreabilidade.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import networkx as nx
import pandas as pd

from simcc.core.settings import Settings
from simcc.schemas_classifier.trace import (
    AreaTraceItem,
    AreaTraceResponse,
    TopicTraceItem,
    TopicTraceResponse,
    SubtopicTraceItem,
    SubtopicTraceResponse,
    ResearcherTraceItem,
    ResearcherTraceResponse,
    ArticleTraceItem,
    ArticleTraceResponse,
)
from simcc.pipeline.constants import TAXONOMY_ORIGIN, TOPIC_ORIGIN, SUBTOPIC_ORIGIN
from simcc.pipeline.graph_utils import get_available_areas, load_graph

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = {
    "id", "title", "year",
    "topic_label", "subtopic_label",
    "researcher_id", "researcher_name",
    "abstract"
}


def _slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def _load_trace(trace_path: Path, min_year: int | None, max_year: int | None) -> pd.DataFrame:
    if not trace_path.exists():
        raise FileNotFoundError(
            "CSV de rastreabilidade não encontrado. Execute o pipeline primeiro."
        )

    df = pd.read_csv(trace_path, encoding="utf-8", dtype=str).fillna("")

    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes no CSV de rastreabilidade: {missing}")

    if min_year is not None or max_year is not None:
        df["_year_int"] = pd.to_numeric(df["year"], errors="coerce")
        if min_year is not None:
            df = df[df["_year_int"] >= min_year]
        if max_year is not None:
            df = df[df["_year_int"] <= max_year]
        df = df.drop(columns=["_year_int"])

    return df


def _ancestor_area_label(graph: nx.DiGraph, node_id: str) -> str:
    for ancestor in nx.ancestors(graph, node_id):
        attrs = graph.nodes[ancestor]
        if attrs.get("origin") == TAXONOMY_ORIGIN and attrs.get("layer") == 1:
            return attrs.get("label", ancestor)
    return ""


def _topic_parent_label(graph: nx.DiGraph, subtopic_node_id: str) -> str:
    for pred in graph.predecessors(subtopic_node_id):
        if graph.nodes[pred].get("origin") == TOPIC_ORIGIN:
            return graph.nodes[pred].get("label", pred)
    return ""


def get_area_trace(settings: Settings, taxonomy_name: str) -> AreaTraceResponse:
    slug_name = _slug(taxonomy_name)
    base_graph_path = settings.processed_dir / f"{slug_name}_base_graph.gpickle"
    final_graph_path = settings.processed_dir / f"{slug_name}_final_graph.gpickle"

    graph_path = final_graph_path if final_graph_path.exists() else base_graph_path
    if not graph_path.exists():
        raise FileNotFoundError(
            f"Grafo da taxonomia '{slug_name}' não encontrado. Execute o pipeline primeiro."
        )
    graph = load_graph(graph_path)

    area_labels = get_available_areas(graph)
    items = [
        AreaTraceItem(number=i, area=area)
        for i, area in enumerate(area_labels, start=1)
    ]
    return AreaTraceResponse(items=items, total=len(items))


def get_topic_trace(settings: Settings, taxonomy_name: str) -> TopicTraceResponse:
    slug_name = _slug(taxonomy_name)
    graph_path = settings.processed_dir / f"{slug_name}_final_graph.gpickle"
    if not graph_path.exists():
        raise FileNotFoundError(
            f"Grafo final da taxonomia '{slug_name}' não encontrado. Execute o pipeline primeiro."
        )
    graph = load_graph(graph_path)

    items: list[TopicTraceItem] = []
    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("origin") != TOPIC_ORIGIN:
            continue
        area = _ancestor_area_label(graph, node_id)
        if not area:
            continue
        items.append(TopicTraceItem(topic=attrs.get("label", node_id), area=area))

    items.sort(key=lambda i: i.topic.lower())
    return TopicTraceResponse(items=items, total=len(items))


def get_subtopic_trace(settings: Settings, taxonomy_name: str) -> SubtopicTraceResponse:
    slug_name = _slug(taxonomy_name)
    graph_path = settings.processed_dir / f"{slug_name}_final_graph.gpickle"
    if not graph_path.exists():
        raise FileNotFoundError(
            f"Grafo final da taxonomia '{slug_name}' não encontrado. Execute o pipeline primeiro."
        )
    graph = load_graph(graph_path)

    items: list[SubtopicTraceItem] = []
    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("origin") != SUBTOPIC_ORIGIN:
            continue
        area = _ancestor_area_label(graph, node_id)
        if not area:
            continue
        topic_label = _topic_parent_label(graph, node_id)
        items.append(SubtopicTraceItem(subtopic=attrs.get("label", node_id), topic=topic_label, area=area))

    items.sort(key=lambda i: i.subtopic.lower())
    return SubtopicTraceResponse(items=items, total=len(items))


def get_researcher_trace(
    settings: Settings,
    taxonomy_name: str,
    min_year: int | None = None,
    max_year: int | None = None,
) -> ResearcherTraceResponse: 
    slug_name = _slug(taxonomy_name)
    trace_path = settings.processed_dir / f"{slug_name}_topic_trace.csv"    
    if not trace_path.exists():
        raise FileNotFoundError(
            f"CSV de rastreabilidade da taxonomia '{slug_name}' não encontrado. Execute o pipeline primeiro."
        )
    df = _load_trace(trace_path, min_year, max_year)
    df = df[df["researcher_id"] != ""]

    grouped = (
        df.groupby(
            ["researcher_name", "area_labels", "topic_label", "subtopic_label"],
            sort=False,
        )
        .size()
        .reset_index(name="article_count")
        .sort_values(
            ["researcher_name", "article_count"],
            ascending=[True, False],
        )
    )

    items = [
        ResearcherTraceItem(
            researcher_name=row["researcher_name"],
            area_labels=row["area_labels"],
            topic_label=row["topic_label"],
            subtopic_label=row["subtopic_label"],
            article_count=int(row["article_count"]),
        )
        for _, row in grouped.iterrows()
    ]

    return ResearcherTraceResponse(items=items, total=len(items))


def get_article_trace(
    settings: Settings,
    taxonomy_name: str,
    min_year: int | None = None,
    max_year: int | None = None,
) -> ArticleTraceResponse:
    slug_name = _slug(taxonomy_name)
    trace_path = settings.processed_dir / f"{slug_name}_topic_trace.csv" 
    if not trace_path.exists():
        raise FileNotFoundError(
            f"CSV de rastreabilidade da taxonomia '{slug_name}' não encontrado. Execute o pipeline primeiro."
        )
    df = _load_trace(trace_path, min_year, max_year)

    items = [
        ArticleTraceItem(                                                
            title=row["title"],
            year=row["year"] or None,
            researcher_name=row["researcher_name"],
            area_labels=row["area_labels"],
            topic_label=row.get("topic_label", ""),
            subtopic_label=row.get("subtopic_label", ""),            
            periodical=row.get("periodical_name", ""),
            qualis=row.get("qualis", ""),
            jcr=row.get("jcr", ""),
            abstract=row.get("abstract", ""),
        )
        for _, row in df.iterrows()
    ]

    return ArticleTraceResponse(items=items, total=len(items))
