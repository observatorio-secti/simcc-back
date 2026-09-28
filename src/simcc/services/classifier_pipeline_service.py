"""
simcc/services/classifier_pipeline_service.py

Encapsula a lógica de execução do pipeline completo de classificação para simcc-back.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
import re
import warnings
from pathlib import Path
from typing import Iterator

import pandas as pd

from simcc.core.settings import Settings
from simcc.pipeline import (
    document_loader, 
    graph_populate,
    graph_topic_integrator,
    graph_utils,     
    topic_hierarchizer, 
    topic_modeling, 
    topic_tracer,
)
from simcc.pipeline.taxonomy_config import TaxonomyConfig
from simcc.repositories.classifier_document_repository import count_pipeline_documents
from simcc.schemas_classifier.pipeline import PipelineDocumentsSummary

logger = logging.getLogger(__name__)

STEP_BASE_GRAPH = 0
STEP_DOCUMENTS = 1
STEP_TOPIC_MODELING = 2
STEP_HIERARCHIZATION = 3
STEP_GRAPH_INTEGRATION = 4
STEP_FINAL_GRAPH = 5
STEP_TRACEABILITY = 6
TOTAL_STEPS = 7

PipelineEvent = tuple[int, str]


def _normalize_name(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def ensure_directories(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class PipelineContext:
    taxonomy_structure: dict | list
    taxonomy_config: TaxonomyConfig    
    taxonomy_name: str
    base_graph_path: Path
    final_graph_path: Path
    trace_csv_path: Path
    topic_csv_path: Path
    topic_mapping_path: Path
    hierarchized_csv_path: Path


def prepare_pipeline(settings: Settings, taxonomy_name: str) -> PipelineContext:
    normalized_name = _normalize_name(taxonomy_name)

    taxonomies_dir = settings.taxonomies_dir
    processed_dir = settings.processed_dir

    ensure_directories(taxonomies_dir)
    ensure_directories(processed_dir)
    
    structure_path = taxonomies_dir / f"{normalized_name}_taxonomy.json"
    if not structure_path.exists():
        # Se não existir com slug, tentar sem slug ou buscar json
        matches = list(taxonomies_dir.glob(f"*{normalized_name}*_taxonomy.json"))
        if matches:
            structure_path = matches[0]
        else:
            raise FileNotFoundError(
                f"Estrutura da taxonomia '{normalized_name}' não encontrada em {structure_path}."
            )
    taxonomy_structure = json.loads(structure_path.read_text(encoding="utf-8"))
    
    config_path = taxonomies_dir / f"{normalized_name}_config.json"
    if not config_path.exists():
        matches = list(taxonomies_dir.glob(f"*{normalized_name}*_config.json"))
        if matches:
            config_path = matches[0]
        else:
            raise FileNotFoundError(
                f"Configuração da taxonomia '{normalized_name}' não encontrada em {config_path}."
            )
    taxonomy_config = TaxonomyConfig.from_json(config_path)

    return PipelineContext(        
        taxonomy_structure=taxonomy_structure,
        taxonomy_config=taxonomy_config,
        taxonomy_name=normalized_name,
        base_graph_path=processed_dir / f"{normalized_name}_base_graph.gpickle",
        final_graph_path=processed_dir / f"{normalized_name}_final_graph.gpickle",
        trace_csv_path=processed_dir / f"{normalized_name}_topic_trace.csv",
        topic_csv_path=processed_dir / f"{normalized_name}_topics_extracted.csv",
        topic_mapping_path=processed_dir / f"{normalized_name}_topic_document_mapping.csv",
        hierarchized_csv_path=processed_dir / f"{normalized_name}_topics_hierarchized.csv",
    )


def get_pipeline_documents_summary(min_year: int = 2017) -> PipelineDocumentsSummary:
    summary = count_pipeline_documents(min_year=min_year)
    return PipelineDocumentsSummary(**summary)


def get_pipeline_documents(
    settings: Settings,
    min_year: int = 2017,
    taxonomy_name: str | None = None,
    taxonomy_structure: dict | list | None = None,
    taxonomy_config: TaxonomyConfig | None = None,
) -> tuple[list[str], pd.DataFrame]:
    _docs_all, df_all = document_loader.load_documents_from_db(min_year=min_year)
    if taxonomy_name and taxonomy_structure is not None:
        return document_loader.filter_documents_by_taxonomy(
            df=df_all,
            taxonomy_name=taxonomy_name,
            taxonomy_structure=taxonomy_structure,
            taxonomy_config=taxonomy_config,
            embedding_model_name=settings.embedding_model,
        )
    return df_all["abstract"].tolist(), df_all


def run_pipeline(settings: Settings, context: PipelineContext, min_year: int = 2017) -> Iterator[PipelineEvent]:
    # Etapa 1: construção do grafo base
    yield STEP_BASE_GRAPH, "⚙️ Gerando grafo inicial com as áreas de base…"
    base_graph = graph_populate.build_and_save_base_graph(
        context.base_graph_path,
        context.taxonomy_structure, 
        context.taxonomy_config
    )
    yield STEP_BASE_GRAPH, "✅ Grafo inicial criado com sucesso!"

    known_area_names = graph_utils.get_available_areas(base_graph)

    # Etapa 2: carregamento dos documentos do PostgreSQL
    yield STEP_BASE_GRAPH, f"📄 Selecionando documentos relevantes do banco de dados para '{context.taxonomy_name}'…"
    docs, df_docs = get_pipeline_documents(
        settings,
        min_year=min_year,
        taxonomy_name=context.taxonomy_name,
        taxonomy_structure=context.taxonomy_structure,
        taxonomy_config=context.taxonomy_config,
    )    
    yield STEP_DOCUMENTS, f"✅ {len(docs)} documentos selecionados do banco para a taxonomia!"

    # Etapa 3: agrupamento temático com BERTopic
    yield STEP_DOCUMENTS, "⚙️ Agrupando os documentos em tópicos temáticos com BERTopic…"
    df_topics_extracted = topic_modeling.generate_topics_from_documents(
        docs,
        df_docs,
        str(context.topic_csv_path),
        str(context.topic_mapping_path),
        settings.embedding_model,
    )
    yield STEP_TOPIC_MODELING, f"✅ {len(df_topics_extracted)} tópicos foram agrupados!"

    # Etapa 4: hierarquização com LLM
    yield STEP_TOPIC_MODELING, "⚙️ Classificando os tópicos de acordo com as áreas de base da taxonomia…"
    yield STEP_TOPIC_MODELING, "⚙️ Estruturando os tópicos em subtópicos com LLM…"
    df_hierarchized = topic_hierarchizer.hierarchize_topics(
        str(context.topic_csv_path),
        str(context.topic_mapping_path),
        str(context.hierarchized_csv_path),
        context.taxonomy_config,
        known_area_names=known_area_names,
    )
    yield STEP_HIERARCHIZATION, f"✅ {len(df_hierarchized)} tópicos foram classificados e estruturados!"

    if df_hierarchized.empty:
        raise ValueError("Nenhum tópico válido com assuntos foi gerado.")

    # Etapa 5: integração dos tópicos no grafo base
    yield STEP_HIERARCHIZATION, "🔗 Integrando os tópicos e subtópicos ao grafo inicial…"
    final_graph = graph_topic_integrator.add_topics_to_graph(
        base_graph, 
        df_hierarchized, 
        settings.embedding_model,
    )
    yield STEP_GRAPH_INTEGRATION, "✅ Os tópicos e subtópicos foram integrados com sucesso!"

    # Etapa 6: salvamento do grafo final
    yield STEP_GRAPH_INTEGRATION, "💾 Salvando o grafo final…"
    graph_utils.save_final_graph(final_graph, context.final_graph_path)
    yield STEP_FINAL_GRAPH, (
        f"✅ O grafo final foi salvo com sucesso: {final_graph.number_of_nodes()} nós"
        f" | {final_graph.number_of_edges()} arestas"
    )

    # Etapa 7: CSV de rastreabilidade
    yield STEP_FINAL_GRAPH, "📊 Mapeando os documentos em áreas, tópicos e subtópicos…"
    df_trace = topic_tracer.build_topic_document_trace(
        str(context.topic_mapping_path),
        str(context.hierarchized_csv_path),
        str(context.trace_csv_path),
        final_graph,
    )
    yield STEP_TRACEABILITY, f"✅ {len(df_trace)} artigos foram mapeados na rastreabilidade!"

    yield STEP_TRACEABILITY, "✅ O pipeline foi completo com sucesso!"
