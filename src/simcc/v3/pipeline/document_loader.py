"""
document_loader.py — Carregamento e limpeza de abstracts e dados de currículos.
 
Ponto de entrada do pipeline de ETL: lê os CSVs de entrada, valida as colunas
esperadas, filtra textos muito curtos e devolve a lista de documentos e o
DataFrame para uso nos módulos subsequentes (topic_modeling, topic_hierarchizer).
 
Colunas suportadas:
  - 'abstract': texto de resumo científico (load_documents)
  - 'content':  texto misto de abstracts e produções bibliográficas (carregar_dados_mistos)
"""
from __future__ import annotations
 
import logging
from pathlib import Path

from typing import Any
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from .embeddings import DEFAULT_EMBEDDING_MODEL, get_embedding_model
from .taxonomy_config import TaxonomyConfig
from simcc.v3.repositories.classifier_document_repository import fetch_documents

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

# Comprimentos mínimos de texto para filtrar entradas sem conteúdo útil.
# Valores abaixo desses limites tendem a gerar tópicos degenerados no BERTopic.
MIN_ABSTRACT_LENGTH = 50
MIN_CONTENT_LENGTH = 15
 
# Colunas aceitas como texto principal em load_documents, em ordem de prioridade.
TEXT_COLUMN_CANDIDATES = ("abstract", "content")


# =============================================================================
# UTILITÁRIOS
# =============================================================================
def _resolve_text_column(df: pd.DataFrame) -> str:
    """
    Identifica a coluna de texto principal no DataFrame.
    Testa as colunas em TEXT_COLUMN_CANDIDATES e retorna a primeira encontrada.
    """
    for col in TEXT_COLUMN_CANDIDATES:
        if col in df.columns:
            return col
    raise ValueError(
        f"O CSV deve conter uma das colunas: {TEXT_COLUMN_CANDIDATES}. "
        f"Colunas encontradas: {list(df.columns)}"
    )
 
 
def _clean_text_column(df: pd.DataFrame, column: str, min_length: int) -> pd.DataFrame:
    """
    Normaliza e filtra a coluna de texto:
    - Converte para string e substitui valores nulos por string vazia
    - Remove linhas cujo texto seja menor que `min_length` caracteres
    """
    df = df.copy()
    df[column] = df[column].astype(str).fillna("")
    return df[df[column].str.len() > min_length]


# =============================================================================
# API PÚBLICA
# =============================================================================
def load_documents(caminho_csv: str | Path) -> tuple[list[str], pd.DataFrame]:
    """
    Carrega abstracts de um arquivo CSV para uso no pipeline de modelagem de tópicos.
 
    Aceita CSVs com coluna 'abstract' ou 'content' como texto principal.
    Filtra textos com menos de MIN_ABSTRACT_LENGTH caracteres, que tendem a
    gerar tópicos degenerados no BERTopic.
 
    Retorna:
        docs: lista de textos para o BERTopic
        df: DataFrame completo com metadados
    """
    print(f"\n{'='*60}")
    print("ETAPA 1: Carregamento dos abstracts")
    print(f"{'='*60}\n")

    caminho = Path(caminho_csv)
    logger.info("Carregando abstracts de:\n %s\n", caminho)

    df = pd.read_csv(caminho, encoding="utf-8")
    text_column = _resolve_text_column(df)
    df = _clean_text_column(df, text_column, MIN_ABSTRACT_LENGTH)
    docs = df[text_column].tolist()
    
    logger.info(
        "✅ %d abstracts carregados (coluna '%s', mín. %d chars)",
        len(docs), text_column, MIN_ABSTRACT_LENGTH,
    )
    return docs, df


def filter_documents_by_taxonomy(
    df: pd.DataFrame,
    taxonomy_name: str,
    taxonomy_structure: dict | list,
    taxonomy_config: TaxonomyConfig | None = None,
    embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
    min_similarity: float = 0.32,
) -> tuple[list[str], pd.DataFrame]:
    """
    Filtra os documentos do DataFrame por relevância semântica à taxonomia alvo.

    Para taxonomias universais/multidisciplinares (como CNPq), mantém todos os documentos.
    Para taxonomias de domínio específico (como Tecnologia, Educação, Estatística, IA),
    calcula a similaridade máxima de cosseno entre o texto do artigo (título + abstract)
    e os nós/áreas da taxonomia.
    """
    norm_name = str(taxonomy_name or "").lower().strip()
    if norm_name in ("cnpq", "universal"):
        df_clean = _clean_text_column(df, "abstract", MIN_ABSTRACT_LENGTH)
        logger.info(
            "Taxonomia universal '%s' — utilizando todos os %d documentos.",
            taxonomy_name, len(df_clean),
        )
        return df_clean["abstract"].tolist(), df_clean

    def _extract_nodes_text(items: Any) -> list[str]:
        texts: list[str] = []
        for item in (items if isinstance(items, list) else [items]):
            if isinstance(item, dict):
                name = item.get("name", "")
                desc = item.get("description", "")
                if desc:
                    texts.append(f"{name}: {desc}")
                elif name:
                    texts.append(name)
                if "children" in item:
                    texts.extend(_extract_nodes_text(item["children"]))
            elif isinstance(item, str) and item.strip():
                texts.append(item.strip())
        return texts

    nodes_text = _extract_nodes_text(taxonomy_structure)
    if taxonomy_config:
        if taxonomy_config.domain_description:
            nodes_text.append(f"{taxonomy_config.name}: {taxonomy_config.domain_description}")
        if taxonomy_config.taxonomy_context:
            nodes_text.append(taxonomy_config.taxonomy_context)

    if not nodes_text:
        df_clean = _clean_text_column(df, "abstract", MIN_ABSTRACT_LENGTH)
        return df_clean["abstract"].tolist(), df_clean

    model = get_embedding_model(embedding_model_name)
    node_embeddings = model.encode(nodes_text)

    df_clean = _clean_text_column(df, "abstract", MIN_ABSTRACT_LENGTH).copy().reset_index(drop=True)
    doc_texts = (df_clean["title"].fillna("") + ". " + df_clean["abstract"].fillna("")).tolist()
    doc_embeddings = model.encode(doc_texts)

    sim_matrix = cosine_similarity(doc_embeddings, node_embeddings)
    max_sims = sim_matrix.max(axis=1)
    df_clean["domain_similarity"] = max_sims

    # Filtro com limiar
    df_filtered = df_clean[df_clean["domain_similarity"] >= min_similarity].reset_index(drop=True)

    # Fallback se ficarem poucos documentos
    if len(df_filtered) < 25 and len(df_clean) >= 25:
        adaptive_thresh = float(df_clean["domain_similarity"].quantile(0.60))
        logger.warning(
            "Poucos documentos (n=%d) com limiar %.2f. Ajustando threshold para %.2f.",
            len(df_filtered), min_similarity, adaptive_thresh,
        )
        df_filtered = df_clean[df_clean["domain_similarity"] >= adaptive_thresh].reset_index(drop=True)

    logger.info(
        "✅ Filtragem por domínio (%s): %d de %d documentos selecionados (sim >= %.2f).",
        taxonomy_name, len(df_filtered), len(df), min_similarity,
    )
    docs = df_filtered["abstract"].tolist()
    return docs, df_filtered


def load_documents_from_db(min_year: int = 2017) -> tuple[list[str], pd.DataFrame]:
    """
    Carrega abstracts diretamente do PostgreSQL para uso no pipeline.
  
    Substitui load_documents() quando a fonte é o banco de dados
    ao invés de um CSV em disco. Mantém o mesmo contrato de retorno:
    (docs, df) — compatível com topic_modeling e demais etapas downstream.
  
    Parâmetros:
        min_year: ano mínimo dos artigos (padrão: 2017).
 
    Retorna:
        docs: lista de abstracts para o BERTopic
        df:   DataFrame completo com metadados (id, researcher_id, title, abstract, year)
    """
    print(f"\n{'='*60}")
    print("ETAPA 1: Carregamento dos abstracts (PostgreSQL)")
    print(f"{'='*60}\n")
 
    df = fetch_documents(min_year=min_year)
    df = _clean_text_column(df, "abstract", MIN_ABSTRACT_LENGTH)
    docs = df["abstract"].tolist()
 
    logger.info(
        "✅ %d documentos carregados do banco (mín. %d chars, ano >= %d)",
        len(docs),
        MIN_ABSTRACT_LENGTH,
        min_year,
    )
    return docs, df


def carregar_dados_mistos(caminho_csv: str | Path) -> tuple[list[str], pd.DataFrame]:
    """
    Carrega um CSV com dados mistos de currículos Lattes (abstracts e produções).
 
    Espera a coluna 'content' como texto principal e, opcionalmente, a coluna
    'type' para log discriminado por tipo de entrada.
    Filtra textos com menos de MIN_CONTENT_LENGTH caracteres.
 
    Retorna:
        docs: lista de textos para o BERTopic
        df: DataFrame completo com metadados
    """
    print(f"\n{'='*60}")
    print("ETAPA 1: Carregamento dos documentos mistos (abstracts + produções)")
    print(f"{'='*60}\n")

    caminho = Path(caminho_csv)
    logger.info("Carregando dados mistos de:\n %s", caminho)
        
    df = pd.read_csv(caminho, encoding="utf-8", quotechar='"')

    if "content" not in df.columns:
        raise ValueError(
            f"O CSV de dados mistos deve conter a coluna 'content'. "
            f"Colunas encontradas: {list(df.columns)}"
        )
    
    df = _clean_text_column(df, "content", 15)
    docs = df["content"].tolist()
    
    if "type" in df.columns:
        qtd_abstracts = len(df[df["type"] == "abstract"])
        qtd_artigos = len(df[df["type"] == "bibliographic_production"])
        logger.info("✅ %d resumos e %d produções bibliográficas carregados.", qtd_abstracts, qtd_artigos)
    else:
        logger.info("✅ %d documentos carregados.", len(docs))

    return docs, df