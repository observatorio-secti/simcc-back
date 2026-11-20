from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from simcc.core.dependencies import get_settings
from simcc.v2.schemas.base import V2Model
from simcc.v2.schemas.city import CityRef
from simcc.v2.schemas.envelope import Meta
from simcc.v2.schemas.filters import ResearcherFilter
from simcc.v2.schemas.graduate_program import GraduateProgramRef
from simcc.v2.schemas.institution import InstitutionRef
from simcc.v2.schemas.params import Pagination
from simcc.v2.schemas.research_group import ResearchGroupRef

FiltersApplied = ResearcherFilter


class MatchItem(V2Model):
    source_type: str
    source_id: Optional[UUID] = None
    title: Optional[str] = None
    year: Optional[int] = None
    snippet: Optional[str] = None


class MatchesSummary(BaseModel):
    total: int
    by_type: dict[str, int]
    items: list[MatchItem]


class Affiliation(V2Model):
    institution: InstitutionRef
    workload: Optional[float] = Field(
        None, description='Regime de trabalho em horas semanais'
    )
    identity_territory: Optional[str] = Field(
        None, description='Território de identidade do vínculo'
    )
    city: Optional[CityRef] = Field(None, description='Cidade do vínculo')


def researcher_image_url(researcher_id: UUID) -> str:
    """Caminho relativo da foto (campo `image`, obsoleto)."""
    return f'/v2/researcher/{researcher_id}/image'


def researcher_absolute_image_url(researcher_id: UUID) -> str:
    """URL absoluta da foto, a partir de `Settings.URL`."""
    base = get_settings().URL.rstrip('/')
    return f'{base}{researcher_image_url(researcher_id)}'


class ResearcherCounts(BaseModel):
    articles: int = 0
    book_chapters: int = 0
    books: int = 0
    patents: int = 0
    software: int = 0
    brands: int = 0


class ResearcherBase(V2Model):
    id: UUID = Field(description='Identificador do pesquisador')
    researcher_id: UUID = Field(
        description='Obsoleto: use `id`', deprecated=True
    )
    name: str
    image_url: str = Field(description='URL absoluta da foto do pesquisador')
    image: str = Field(
        description='Obsoleto: caminho relativo da foto; use `image_url`',
        deprecated=True,
    )
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

    @model_validator(mode='before')
    @classmethod
    def _fill_ids_and_image(cls, data: Any) -> Any:
        """Aceita `id` ou `researcher_id` e deriva os campos de imagem."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        rid = data.get('id') or data.get('researcher_id')
        if rid is None:
            return data
        data.setdefault('id', rid)
        data.setdefault('researcher_id', rid)
        data.setdefault('image', researcher_image_url(rid))
        data.setdefault('image_url', researcher_absolute_image_url(rid))
        return data


class ResearcherSummary(ResearcherBase):
    matches: Optional[MatchesSummary] = None


class ResearcherIdentifiers(V2Model):
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


class GraduateProgramLink(V2Model):
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
    value: str = Field(description='Valor a enviar no filtro correspondente')
    label: str = Field(description='Texto de exibição')
    count: int = Field(description='Itens do resultado com esse valor')
    acronym: Optional[str] = Field(
        None, description='Sigla, quando o valor for uma entidade'
    )
    selected: bool = Field(
        False, description='Se o valor está aplicado no filtro atual'
    )


class FacetResult(BaseModel):
    param: Union[str, list[str], None] = Field(
        None,
        description=(
            'Parâmetro de filtro correspondente à faceta. Lista quando a '
            'faceta mapeia para um intervalo (ex.: year → year_start, '
            'year_end)'
        ),
    )
    total: int = Field(
        description='Quantidade de valores distintos com resultados'
    )
    items: list[FacetItem] = Field(
        description='Valores mais frequentes e os valores selecionados'
    )


class Sort(BaseModel):
    by: str = Field(description='Campo de ordenação aplicado')
    order: str = Field(description='Direção aplicada (asc/desc)')

    @model_validator(mode='before')
    @classmethod
    def _from_sort_params(cls, data: Any) -> Any:
        """Aceita os parâmetros de ordenação (`sort_by`/`sort_order`)."""
        if isinstance(data, BaseModel):
            data = data.model_dump()
        if isinstance(data, dict) and 'sort_by' in data:
            return {'by': data['sort_by'], 'order': data['sort_order']}
        return data


class SearchResponse(BaseModel):
    data: list[ResearcherSummary]
    pagination: Pagination
    filters_applied: ResearcherFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None
