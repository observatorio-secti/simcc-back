from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from simcc.v2.schemas.filters import ResearcherFilter

FiltersApplied = ResearcherFilter


class Researcher(BaseModel):
    researcher_id: UUID
    name: str


class Pagination(BaseModel):
    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class Sort(BaseModel):
    by: str
    order: str


class Meta(BaseModel):
    took_ms: int
    cached: bool
    timestamp: datetime


class SearchResponse(BaseModel):
    data: List[Researcher]
    pagination: Pagination
    filters_applied: ResearcherFilter
    sort: Sort
    meta: Meta
    facets: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
