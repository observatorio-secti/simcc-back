"""
schemas_classifier/taxonomy_generator.py — Schemas para geração de taxonomia via LLM.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class TaxonomyArea(BaseModel):
    key: str = Field(description="Chave curta sem espaços.")
    title: str = Field(description="Título legível da área.")
    description: str = Field(description="Descrição de 1-2 frases.")


class GeneratedTaxonomyConfig(BaseModel):
    name: str
    domain_description: str
    area_examples: list[str]
    taxonomy_context: str
    origin_label: str = "TAXONOMY"
    node_color: str = "#97C2FC"    
    area_filter_layer: int = 1
    areas: list[TaxonomyArea]


class TaxonomyGenerateRequest(BaseModel):
    prompt: str = Field(
        description="Descrição livre da taxonomia desejada.",
        min_length=3,
    )


class TaxonomyGenerateResponse(BaseModel):
    generated: GeneratedTaxonomyConfig


class TaxonomySaveRequest(BaseModel):
    config: GeneratedTaxonomyConfig


class TaxonomySaveResponse(BaseModel):
    taxonomy_name: str
    config_path: str
    taxonomy_path: str
    message: str
