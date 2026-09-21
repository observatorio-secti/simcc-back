from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


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


class FiltersApplied(BaseModel):
    q: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    institution_id: Optional[UUID] = None
    graduate_program_id: Optional[UUID] = None


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
    filters_applied: FiltersApplied
    sort: Sort
    meta: Meta
    facets: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
