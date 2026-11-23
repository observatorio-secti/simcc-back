"""Schemas dos catálogos v2: instituições e programas de pós-graduação."""

from datetime import date
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from simcc.v2.schemas.base import V2Model
from simcc.v2.schemas.envelope import Meta
from simcc.v2.schemas.institution import InstitutionRef
from simcc.v2.schemas.params import Pagination
from simcc.v2.schemas.researcher import FacetResult, Sort


class CatalogItem(V2Model):
    id: UUID = Field(description='Identificador do recurso')
    name: str = Field(description='Nome do recurso')
    acronym: Optional[str] = Field(None, description='Sigla do recurso')


class CatalogSort(BaseModel):
    """Ordenação das listagens de catálogo."""

    sort_by: Literal['name', 'acronym'] = Field(
        'name', description='Campo para ordenação'
    )
    sort_order: Literal['asc', 'desc'] = Field(
        'asc', description='Direção da ordenação (asc/desc)'
    )


def _split(v: Any) -> Any:
    if isinstance(v, str):
        return [v]
    return v


# =========================================================================
# Instituições
# =========================================================================


class InstitutionFilter(BaseModel):
    q: Optional[str] = Field(
        None, description='Termo para busca por nome ou sigla'
    )


class InstitutionCounts(BaseModel):
    researchers: int = Field(0, description='Pesquisadores vinculados')
    graduate_programs: int = Field(
        0, description='Programas de pós-graduação da instituição'
    )
    scholarship_holders: int = Field(
        0, description='Pesquisadores bolsistas vinculados à instituição'
    )
    research_groups: int = Field(
        0, description='Grupos de pesquisa vinculados à instituição'
    )
    labs: int = Field(0, description='Laboratórios vinculados à instituição')


class ScholarshipBreakdownItem(BaseModel):
    modality: Optional[str] = Field(None, description='Modalidade da bolsa')
    category_level: Optional[str] = Field(
        None, description='Categoria/nível (ex.: 1A, 1B, 2)'
    )
    researchers: int = Field(
        description='Quantidade distinta de pesquisadores bolsistas'
    )


class InstitutionDetail(InstitutionRef):
    description: Optional[str] = Field(None, description='Descrição')
    lattes_id: Optional[str] = Field(None, description='Código no Lattes')
    latitude: Optional[float] = Field(None, description='Latitude')
    longitude: Optional[float] = Field(None, description='Longitude')
    counts: InstitutionCounts = Field(default_factory=InstitutionCounts)
    scholarships: list[ScholarshipBreakdownItem] = Field(
        default_factory=list,
        description='Detalhamento de bolsistas por modalidade e nível',
    )


class InstitutionListResponse(BaseModel):
    data: list[InstitutionRef] = Field(description='Lista de instituições')
    pagination: Pagination = Field(description='Metadados de paginação')
    filters_applied: InstitutionFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# Programas de pós-graduação
# =========================================================================


GRADUATE_PROGRAM_FACETS = (
    'institution',
    'area',
    'modality',
    'rating',
    'state',
    'city',
    'identity_territory',
    'territory_city',
)


class GraduateProgramFilter(BaseModel):
    """Filtros de `GET /v2/graduate-program`. Listas são repetidas na URL
    e combinadas com OU; filtros diferentes, com E."""

    q: Optional[str] = Field(
        None, description='Termo para busca por nome ou sigla'
    )
    institution_id: list[UUID] = Field(
        default_factory=list, description='IDs das instituições'
    )
    area: list[str] = Field(
        default_factory=list, description='Área de avaliação CAPES'
    )
    modality: list[str] = Field(
        default_factory=list,
        description='Modalidade (ex.: Acadêmico, Profissional)',
    )
    rating: list[str] = Field(
        default_factory=list, description='Conceito CAPES'
    )
    state: list[str] = Field(default_factory=list, description='UF')
    city: list[str] = Field(default_factory=list, description='Cidade')
    city_code: list[str] = Field(
        default_factory=list,
        description='Código IBGE (7 dígitos) do município da sede',
    )
    identity_territory: list[str] = Field(
        default_factory=list,
        description=(
            'Território de identidade da sede: código SEI (1 a 27) ou nome'
        ),
    )

    split_lists = field_validator(
        'institution_id',
        'area',
        'modality',
        'rating',
        'state',
        'city',
        'city_code',
        'identity_territory',
        mode='before',
    )(_split)


class GraduateProgramOptions(BaseModel):
    facets: list[str] = Field(
        default=[],
        description=(
            f'Lista de facets opt-in ({", ".join(GRADUATE_PROGRAM_FACETS)})'
        ),
    )
    facet_limit: int = Field(
        20, ge=1, le=100, description='Número máximo de valores por facet'
    )

    @field_validator('facets', mode='before')
    @classmethod
    def _split_facets(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, (list, tuple, set)):
            return []
        values = [
            part.strip()
            for item in v
            if isinstance(item, str)
            for part in item.split(',')
            if part.strip()
        ]
        invalid = [f for f in values if f not in GRADUATE_PROGRAM_FACETS]
        if invalid:
            raise ValueError(
                f'Facets desconhecidos: {invalid}. '
                f'Permitidos: {list(GRADUATE_PROGRAM_FACETS)}'
            )
        return values


class GraduateProgramSummary(CatalogItem):
    institution_id: Optional[UUID] = Field(
        None, description='Instituição do programa'
    )
    area: Optional[str] = Field(None, description='Área de avaliação')
    modality: Optional[str] = Field(None, description='Modalidade')
    rating: Optional[str] = Field(None, description='Conceito CAPES')
    state: Optional[str] = Field(None, description='UF')
    city: Optional[str] = Field(None, description='Cidade')


class ResearchLine(V2Model):
    name: str = Field(description='Nome da linha de pesquisa')
    area: Optional[str] = Field(None, description='Área da linha')
    start_year: Optional[int] = Field(None, description='Ano de início')
    end_year: Optional[int] = Field(None, description='Ano de término')


class GraduateProgramCounts(BaseModel):
    researchers: int = Field(0, description='Docentes vinculados')


class GraduateProgramDetail(GraduateProgramSummary):
    institution: Optional[InstitutionRef] = None
    code: Optional[str] = Field(None, description='Código CAPES')
    name_en: Optional[str] = Field(None, description='Nome em inglês')
    type: Optional[str] = Field(None, description='Tipo (ex.: Mestrado)')
    description: Optional[str] = Field(None, description='Descrição')
    site: Optional[str] = Field(None, description='Site do programa')
    coordinator: Optional[str] = Field(None, description='Coordenação')
    email: Optional[str] = Field(None, description='E-mail de contato')
    phone: Optional[str] = Field(None, description='Telefone de contato')
    start: Optional[date] = Field(None, description='Data de início')
    research_lines: list[ResearchLine] = Field(
        default_factory=list, description='Linhas de pesquisa'
    )
    counts: GraduateProgramCounts = Field(
        default_factory=GraduateProgramCounts
    )


class CatalogResponse(BaseModel):
    """Resposta da listagem de programas de pós-graduação."""

    data: list[GraduateProgramSummary] = Field(
        description='Lista de programas'
    )
    pagination: Pagination = Field(description='Metadados de paginação')
    filters_applied: GraduateProgramFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None
