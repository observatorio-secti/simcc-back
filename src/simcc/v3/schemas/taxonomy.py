"""
v3/schemas/taxonomy.py — Schemas Pydantic para os endpoints de taxonomia.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel

NodeOrigin = Literal["TAXONOMY", "TOPIC", "SUBTOPIC"]


class NodeData(BaseModel):
    id: str
    label: str
    origin: NodeOrigin
    layer: int    
    color: str
    size: Optional[int] = None
    num_documents: Optional[int] = None
    coverage: Optional[str] = None


class EdgeData(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    weight: float
    similarity_score: Optional[float] = None


class NodeElement(BaseModel):
    data: NodeData


class EdgeElement(BaseModel):
    data: EdgeData


GraphElement = NodeElement | EdgeElement


class GraphSummary(BaseModel):
    total_nodes: int
    total_edges: int
    nodes_by_origin: dict[str, int]


class GraphResponse(BaseModel):
    taxonomy_name: str
    elements: list[GraphElement]
    summary: GraphSummary


class TaxonomyItem(BaseModel):    
    taxonomy_name: str
    total_nodes: int 
    domain_description: str | None = None


class TaxonomyListResponse(BaseModel):
    items: list[TaxonomyItem]
    total: int
