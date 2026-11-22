"""Schemas da Fase 2: revistas, bolsistas, termos e indicadores."""

from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from simcc.v2.schemas.base import V2Model
from simcc.v2.schemas.envelope import Meta
from simcc.v2.schemas.kinds import ProductionKind
from simcc.v2.schemas.params import Pagination
from simcc.v2.schemas.production import ProductionBaseFilter
from simcc.v2.schemas.qualis import (
    QualisFilterValue,
    QualisRank,
    QualisStatus,
    parse_jcr,
    parse_qualis,
)
from simcc.v2.schemas.researcher import FacetResult, Sort


def _split_facets(allowed: tuple[str, ...]):
    def validator(cls, v: Any) -> list[str]:
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
        invalid = [f for f in values if f not in allowed]
        if invalid:
            raise ValueError(
                f'Facets desconhecidos: {invalid}. Permitidos: {list(allowed)}'
            )
        return values

    return field_validator('facets', mode='before')(classmethod(validator))


# =========================================================================
# Revistas
# =========================================================================

MAGAZINE_FACETS = ('qualis',)


class MagazineFilter(BaseModel):
    q: Optional[str] = Field(None, description='Busca pelo nome da revista')
    issn: list[str] = Field(default_factory=list, description='ISSN')
    qualis: list[QualisFilterValue] = Field(
        default_factory=list,
        description='Estrato Qualis ou ausência (not_rated, not_applicable)',
    )


class MagazineSort(BaseModel):
    sort_by: Literal['name', 'jcr'] = Field(
        'name', description='Campo para ordenação'
    )
    sort_order: Optional[Literal['asc', 'desc']] = Field(
        None,
        description='Direção (padrão: asc para name, desc para jcr)',
    )

    @model_validator(mode='after')
    def _default_order(self) -> 'MagazineSort':
        if self.sort_order is None:
            self.sort_order = 'desc' if self.sort_by == 'jcr' else 'asc'
        return self


class MagazineOptions(BaseModel):
    facets: list[str] = Field(
        default=[], description='Facets opt-in (qualis)'
    )
    facet_limit: int = Field(20, ge=1, le=100)

    split_facets = _split_facets(MAGAZINE_FACETS)


class Magazine(V2Model):
    id: UUID = Field(description='Identificador da revista')
    name: Optional[str] = Field(None, description='Nome da revista')
    issn: Optional[str] = Field(None, description='ISSN')
    qualis: Optional[QualisRank] = Field(None, description='Estrato Qualis')
    qualis_status: Optional[QualisStatus] = Field(
        None, description='Motivo da ausência de estrato'
    )
    jcr: Optional[float] = Field(None, description='Fator de impacto JCR')
    jcr_link: Optional[str] = Field(None, description='Link do JCR')
    reference_period: Optional[str] = Field(
        None, description='Período de referência do Qualis'
    )

    @model_validator(mode='before')
    @classmethod
    def _type_values(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        rank, status = parse_qualis(data.get('qualis'))
        data['qualis'] = rank
        data.setdefault('qualis_status', status or ('not_rated' if rank is None else None))
        data['jcr'] = parse_jcr(data.get('jcr'))
        return data


class MagazineListResponse(BaseModel):
    data: list[Magazine]
    pagination: Pagination
    filters_applied: MagazineFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# Bolsistas
# =========================================================================

SCHOLARSHIP_FACETS = (
    'institution',
    'graduate_program',
    'modality',
    'category_level',
)


class ScholarshipFilter(BaseModel):
    researcher_id: list[UUID] = Field(
        default_factory=list, description='IDs dos pesquisadores'
    )
    institution_id: list[UUID] = Field(
        default_factory=list, description='IDs das instituições de vínculo'
    )
    graduate_program_id: list[UUID] = Field(
        default_factory=list, description='IDs dos programas de pós'
    )
    modality: list[str] = Field(
        default_factory=list,
        description='Modalidade (ex.: Produtividade em Pesquisa)',
    )
    category_level: list[str] = Field(
        default_factory=list, description='Categoria/nível (ex.: 1A, 2)'
    )


class ScholarshipSort(BaseModel):
    sort_by: Literal['researcher_name', 'modality', 'category_level'] = Field(
        'researcher_name', description='Campo para ordenação'
    )
    sort_order: Literal['asc', 'desc'] = Field(
        'asc', description='Direção da ordenação'
    )


class ScholarshipOptions(BaseModel):
    facets: list[str] = Field(
        default=[],
        description=(
            'Facets opt-in (institution, graduate_program, modality, '
            'category_level)'
        ),
    )
    facet_limit: int = Field(20, ge=1, le=100)

    split_facets = _split_facets(SCHOLARSHIP_FACETS)


class ScholarshipResearcher(V2Model):
    id: UUID
    name: str


class Scholarship(V2Model):
    id: UUID = Field(description='Identificador do registro de fomento')
    researcher: ScholarshipResearcher
    modality: Optional[str] = Field(None, description='Modalidade')
    category_level: Optional[str] = Field(None, description='Nível')
    call_title: Optional[str] = Field(None, description='Chamada')
    funding_program: Optional[str] = Field(
        None, description='Programa de fomento'
    )
    institute: Optional[str] = Field(None, description='Instituição')
    aid_quantity: Optional[int] = Field(None, description='Auxílios')
    scholarship_quantity: Optional[int] = Field(None, description='Bolsas')


class ScholarshipListResponse(BaseModel):
    data: list[Scholarship]
    pagination: Pagination
    filters_applied: ScholarshipFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# Termos do pesquisador
# =========================================================================


class TermsParams(BaseModel):
    limit: int = Field(30, ge=1, le=100, description='Quantidade de termos')


class Term(BaseModel):
    term: str = Field(description='Palavra (sem acento, minúscula)')
    frequency: int = Field(description='Títulos em que a palavra aparece')


class TermsResponse(BaseModel):
    data: list[Term]
    meta: Meta


# =========================================================================
# Indicadores
# =========================================================================


class SeriesPoint(BaseModel):
    period: int = Field(description='Ano')
    value: int = Field(description='Quantidade de produções no ano')


class ProductionMetricResponse(BaseModel):
    kind: ProductionKind = Field(description='Tipo de produção contado')
    data: list[SeriesPoint] = Field(description='Série anual, ano crescente')
    filters_applied: ProductionBaseFilter
    meta: Meta
