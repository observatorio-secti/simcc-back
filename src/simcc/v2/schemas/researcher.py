from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from simcc.v2.schemas.city import CityRef
from simcc.v2.schemas.filters import ResearcherFilter
from simcc.v2.schemas.institution import InstitutionRef
from simcc.v2.schemas.params import Pagination

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


class Affiliation(BaseModel):
    institution: InstitutionRef
    workload: Optional[float] = Field(
        None, description='Regime de trabalho em horas semanais'
    )
    identity_territory: Optional[str] = Field(
        None, description='Território de identidade do vínculo'
    )
    city: Optional[CityRef] = Field(None, description='Cidade do vínculo')


class Researcher(BaseModel):
    researcher_id: UUID
    name: str
    affiliations: list[Affiliation] = []
    matches: Optional[MatchesSummary] = None


class FacetItem(BaseModel):
    value: str
    label: str
    count: int


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
