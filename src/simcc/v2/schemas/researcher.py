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
from simcc.v2.schemas.kinds import MatchSourceType, SourceType
from simcc.v2.schemas.params import Pagination
from simcc.v2.schemas.research_group import ResearchGroupRef

FiltersApplied = ResearcherFilter


class MatchItem(V2Model):
    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'source_type': 'article',
                    'source_id': '0b6f1c1e-2d4a-4c55-9f0e-2b7f3c9d1a11',
                    'title': 'Redes neurais aplicadas a solos',
                    'year': 2023,
                    'snippet': 'Redes neurais aplicadas a solos',
                    'highlights': [[0, 13]],
                }
            ]
        }
    }

    source_type: MatchSourceType
    source_id: Optional[UUID] = None
    title: Optional[str] = None
    year: Optional[int] = None
    snippet: Optional[str] = Field(
        None, description='Trecho em texto puro, sem marcação'
    )
    highlights: list[tuple[int, int]] = Field(
        default_factory=list,
        description=(
            'Intervalos [início, fim) destacados em `snippet`, em unidades '
            'UTF-16 (as de String.slice no JavaScript)'
        ),
    )


class MatchesSummary(BaseModel):
    total: int
    by_type: dict[SourceType, int]
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


# Contadores que vêm de `mv_researcher_search`/`researcher_production`
MV_COUNT_FIELDS = (
    'articles',
    'book_chapters',
    'books',
    'patents',
    'software',
    'brands',
)


class ResearcherCounts(BaseModel):
    articles: int = 0
    book_chapters: int = 0
    books: int = 0
    patents: int = 0
    software: int = 0
    brands: int = 0
    guidance: int = Field(0, description='Orientações')
    reports: int = Field(0, description='Relatórios técnicos')


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


class Education(V2Model):
    degree: str = Field(description='Nível (ex.: Doutorado)')
    course: Optional[str] = Field(None, description='Nome do curso')
    institution: Optional[str] = Field(None, description='Instituição')
    start_year: Optional[int] = Field(None, description='Ano de início')
    end_year: Optional[int] = Field(None, description='Ano de conclusão')
    status: Optional[str] = Field(None, description='Situação')
    keywords: list[str] = Field(
        default_factory=list, description='Palavras-chave'
    )


class ProfessionalExperience(V2Model):
    organization: str = Field(description='Instituição ou empresa')
    start_year: Optional[int] = Field(None, description='Ano de início')
    end_year: Optional[int] = Field(
        None, description='Ano de término (ausente se atual)'
    )
    employment_type: Optional[str] = Field(None, description='Vínculo')
    functional_classification: Optional[str] = Field(
        None, description='Enquadramento funcional'
    )
    workload_hours_weekly: Optional[int] = Field(
        None, description='Carga horária semanal'
    )
    exclusive_dedication: Optional[bool] = Field(
        None, description='Dedicação exclusiva'
    )
    additional_info: Optional[str] = Field(
        None, description='Outras informações'
    )


class Foment(V2Model):
    modality_code: Optional[str] = Field(None, description='Código')
    modality: Optional[str] = Field(
        None, description='Modalidade (ex.: Produtividade em Pesquisa)'
    )
    category_level: Optional[str] = Field(
        None, description='Categoria/nível (ex.: 1A)'
    )
    call_title: Optional[str] = Field(None, description='Chamada')
    funding_program: Optional[str] = Field(
        None, description='Programa de fomento'
    )
    institute: Optional[str] = Field(None, description='Instituição')
    aid_quantity: Optional[int] = Field(None, description='Auxílios')
    scholarship_quantity: Optional[int] = Field(None, description='Bolsas')


DETAIL_INCLUDES = ('education', 'experience', 'foment')


class ResearcherDetailOptions(BaseModel):
    include: list[str] = Field(
        default=[],
        description=(
            f'Seções opcionais do perfil ({", ".join(DETAIL_INCLUDES)})'
        ),
    )

    @model_validator(mode='before')
    @classmethod
    def _split_include(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw = data.get('include') or []
        if isinstance(raw, str):
            raw = [raw]
        values = [
            part.strip()
            for item in raw
            if isinstance(item, str)
            for part in item.split(',')
            if part.strip()
        ]
        invalid = [v for v in values if v not in DETAIL_INCLUDES]
        if invalid:
            raise ValueError(
                f'Includes desconhecidos: {invalid}. '
                f'Permitidos: {list(DETAIL_INCLUDES)}'
            )
        return {**data, 'include': values}


class ResearcherDetail(ResearcherBase):
    abstract: Optional[str] = None
    abstract_ai: Optional[str] = None
    identifiers: ResearcherIdentifiers
    bibliometrics: Optional[Bibliometrics] = Field(
        None, description='Métricas do OpenAlex, quando disponíveis'
    )
    graduate_programs: list[GraduateProgramLink] = []
    research_groups: list[ResearchGroupRef] = []
    education: Optional[list[Education]] = Field(
        None, description='Formação (com include=education)'
    )
    experience: Optional[list[ProfessionalExperience]] = Field(
        None, description='Experiência profissional (com include=experience)'
    )
    foment: Optional[list[Foment]] = Field(
        None, description='Bolsas e auxílios (com include=foment)'
    )


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
    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'param': 'institution_id',
                    'total': 2,
                    'items': [
                        {
                            'value': '3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90',
                            'label': 'Universidade Estadual de Santa Cruz',
                            'count': 120,
                            'acronym': 'UESC',
                            'selected': True,
                        }
                    ],
                }
            ]
        }
    }

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
