from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from simcc.v2.schemas.city import CityRef
from simcc.v2.schemas.filters import ResearcherFilter
from simcc.v2.schemas.graduate_program import GraduateProgramRef
from simcc.v2.schemas.institution import InstitutionRef
from simcc.v2.schemas.params import Pagination
from simcc.v2.schemas.research_group import ResearchGroupRef

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


def researcher_image_url(researcher_id: UUID) -> str:
    return f'/v2/researcher/{researcher_id}/image'


class ResearcherCounts(BaseModel):
    articles: int = 0
    book_chapters: int = 0
    books: int = 0
    patents: int = 0
    software: int = 0
    brands: int = 0


class ResearcherBase(BaseModel):
    researcher_id: UUID
    name: str
    image: str = Field(description='URL da foto do pesquisador')
    graduation: Optional[str] = Field(None, description='Maior titulação')
    classification: Optional[str] = Field(
        None, description='Classificação do pesquisador'
    )
    lattes_update: Optional[datetime] = Field(
        None, description='Data da última atualização do Lattes'
    )
    affiliations: list[Affiliation] = []
    counts: ResearcherCounts = Field(
        default_factory=ResearcherCounts,
        description='Contadores de produção',
    )


class ResearcherSummary(ResearcherBase):
    matches: Optional[MatchesSummary] = None


class ResearcherIdentifiers(BaseModel):
    lattes_id: str
    lattes_10_id: Optional[str] = None
    orcid: Optional[str] = None
    scopus: Optional[str] = None
    openalex: Optional[str] = None


class Bibliometrics(BaseModel):
    h_index: Optional[int] = None
    i10_index: Optional[int] = None
    cited_by_count: Optional[int] = None
    works_count: Optional[int] = None


class GraduateProgramLink(BaseModel):
    program: GraduateProgramRef
    type: Optional[str] = Field(
        None, description='Tipo de vínculo com o programa'
    )


class ResearcherDetail(ResearcherBase):
    abstract: Optional[str] = None
    abstract_ai: Optional[str] = None
    identifiers: ResearcherIdentifiers
    bibliometrics: Optional[Bibliometrics] = Field(
        None, description='Métricas do OpenAlex, quando disponíveis'
    )
    graduate_programs: list[GraduateProgramLink] = []
    research_groups: list[ResearchGroupRef] = []


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
    data: list[ResearcherSummary]
    pagination: Pagination
    filters_applied: ResearcherFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, list[FacetItem]]] = None
    summary: Optional[dict[str, Any]] = None
