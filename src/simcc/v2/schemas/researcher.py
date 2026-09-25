from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel

from simcc.v2.schemas.filters import ResearcherFilter

FiltersApplied = ResearcherFilter


class MatchItem(BaseModel):
    source_type: str
    source_id: Optional[UUID] = None
    title: Optional[str] = None
    year: Optional[int] = None
    snippet: Optional[str] = None


class MatchesSummary(BaseModel):
    total: int
    by_type: dict[str, int]
    items: list[MatchItem]


class Researcher(BaseModel):
    researcher_id: UUID
    name: str
    matches: Optional[MatchesSummary] = None


class FacetItem(BaseModel):
    value: str
    label: str
    count: int


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
    data_as_of: Optional[datetime] = None


class SearchResponse(BaseModel):
    data: list[Researcher]
    pagination: Pagination
    filters_applied: ResearcherFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, list[FacetItem]]] = None
    summary: Optional[dict[str, Any]] = None
