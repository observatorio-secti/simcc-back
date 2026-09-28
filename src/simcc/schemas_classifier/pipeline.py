"""
schemas_classifier/pipeline.py — Schemas Pydantic para os endpoints do pipeline.
"""
from __future__ import annotations

from pydantic import BaseModel


class PipelineDocumentsSummary(BaseModel):
    min_year: int
    total_articles: int
    total_researchers: int
