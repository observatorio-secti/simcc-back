"""
repositories/classifier_document_repository.py — Acesso aos documentos no PostgreSQL.

Responsabilidades:
  - Buscar artigos com abstract válido para alimentar o pipeline do classificador
    (via JOIN com openalex_article e researcher)
  - Manter contrato de retorno em DataFrame do pandas.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd
import psycopg2
import psycopg2.extras

from simcc.core.settings import Settings

logger = logging.getLogger(__name__)

_VALID_TYPES = ("ARTICLE",)


def _normalize_title(title: object) -> str:
    return re.sub(r"\s+", " ", str(title or "").strip().lower())


def _deduplicate_documents(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove artigos duplicados por (researcher_id, título normalizado, ano);
    mantém a primeira ocorrência.
    """
    if df.empty:
        return df

    key = (
        df["researcher_id"].astype(str)
        + "|" + df["title"].map(_normalize_title)
        + "|" + df["year"].astype(str)
    )
    before = len(df)
    df = df.loc[~key.duplicated()].reset_index(drop=True)
    removed = before - len(df)
    if removed:
        logger.info(
            "Removidas %d entradas duplicadas de artigos (mesmo pesquisador+título+ano).",
            removed,
        )
    return df


def get_connection():
    settings = Settings()
    url = settings.CLASSIFIER_DATABASE_URL or settings.DATABASE_URL
    # Se a URL for postgresql+asyncpg://... converter para postgresql://...
    dsn = url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


_FETCH_DOCUMENTS_SQL = """
SELECT
    bp.id,
    bp.researcher_id,
    r.name AS researcher_name,
    bp.title,
    opa.abstract,
    bp.year,
    bpa.periodical_magazine_name AS periodical_name, 
    bpa.qualis,
    bpa.jcr
FROM bibliographic_production bp
JOIN bibliographic_production_article bpa ON bp.id = bpa.bibliographic_production_id
JOIN openalex_article opa ON bp.id = opa.article_id
JOIN researcher r          ON bp.researcher_id = r.id
WHERE bp.type = 'ARTICLE'
  AND opa.abstract IS NOT NULL
  AND opa.abstract <> ''
  AND bp.year::INT >= %(min_year)s
ORDER BY bp.year DESC, bp.id
"""

def fetch_documents(min_year: int = 2017) -> pd.DataFrame:
    """
    Retorna DataFrame com artigos que já possuem abstract em openalex_article.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_FETCH_DOCUMENTS_SQL, {"min_year": min_year})
            rows = cur.fetchall()

        df = pd.DataFrame(
            rows,
            columns=[
                "id", "researcher_id", "researcher_name", 
                "title", "abstract", "year",
                "periodical_name", "qualis", "jcr"
            ],
        )
        df = _deduplicate_documents(df)
        logger.info(
            "Artigos para o pipeline: %d (com abstract, ano >= %d)",
            len(df), min_year,
        )
        return df
    finally:
        conn.close()


def count_pipeline_documents(min_year: int = 2017) -> dict:
    df = fetch_documents(min_year=min_year)

    total_articles = int(len(df))
    total_researchers = int(df["researcher_id"].nunique()) if not df.empty else 0

    logger.info(
        "Resumo do pipeline (ano >= %d): %d artigos únicos | %d pesquisadores únicos",
        min_year, total_articles, total_researchers,
    )

    return {
        "min_year": min_year,
        "total_articles": total_articles,
        "total_researchers": total_researchers,
    }
