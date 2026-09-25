from typing import Literal, Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from simcc.v2.schemas.params import PaginationParams, SearchOptions, SortParams


class BaseFilter(BaseModel):
    q: Optional[str] = Field(None, description='Termo de busca textual')


class BaseTemporalFilter(BaseFilter):
    year_start: Optional[int] = Field(
        None, description='Ano inicial do intervalo temporal'
    )
    year_end: Optional[int] = Field(
        None, description='Ano final do intervalo temporal'
    )


SourceType = Literal['ARTICLE', 'BOOK', 'BOOK_CHAPTER', 'PATENT', 'SOFTWARE']
Classification = Literal['A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'E+', 'E']


class ResearcherFilter(BaseTemporalFilter):
    """Filtros de `GET /v2/researcher`, lidos direto da query string.

    Para adicionar um filtro: declare o campo aqui e registre a condição em
    `repositories/researcher_filters.py`. Listas são repetidas na URL
    (`?city_id=a&city_id=b`) e combinadas com OU; filtros diferentes, com E.
    """

    q: Optional[str] = Field(
        None,
        description='Busca textual no perfil (nome e resumo) e nas produções',
    )
    year_start: Optional[int] = Field(
        None, description='Ano inicial de produção'
    )
    year_end: Optional[int] = Field(None, description='Ano final de produção')
    institution_id: list[UUID] = Field(
        default_factory=list, description='IDs das instituições de vínculo'
    )
    graduate_program_id: list[UUID] = Field(
        default_factory=list, description='IDs dos programas de pós-graduação'
    )
    city_id: list[UUID] = Field(
        default_factory=list, description='IDs das cidades de vínculo'
    )
    identity_territory: list[str] = Field(
        default_factory=list,
        description='Territórios de identidade dos vínculos',
    )
    graduation: list[str] = Field(
        default_factory=list, description='Maior titulação (ex.: Doutorado)'
    )
    classification: list[Classification] = Field(
        default_factory=list, description='Classificação do pesquisador'
    )
    source_type: list[SourceType] = Field(
        default_factory=list,
        description=(
            'Tipos de produção considerados. Com `q`, restringe as obras '
            'que podem casar com a busca; sem `q`, exige ao menos uma obra '
            'desses tipos'
        ),
    )

    @model_validator(mode='after')
    def validate_year_range(self) -> 'ResearcherFilter':
        if (
            self.year_start is not None
            and self.year_end is not None
            and self.year_start > self.year_end
        ):
            raise ValueError(
                'year_start must be less than or equal to year_end'
            )
        return self


KNOWN_RESEARCHER_PARAMS = frozenset().union(
    ResearcherFilter.model_fields,
    PaginationParams.model_fields,
    SortParams.model_fields,
    SearchOptions.model_fields,
)


def validate_unknown_researcher_params(request: Request) -> None:
    """Valida se há parâmetros desconhecidos na query string."""
    for param_name in request.query_params:
        if param_name not in KNOWN_RESEARCHER_PARAMS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Parâmetro desconhecido: '{param_name}'",
            )


class ProductionFilter(BaseTemporalFilter):
    institution_id: Optional[UUID] = None
    graduate_program_id: Optional[UUID] = None
    researcher_id: Optional[UUID] = None
    type: Optional[str] = None
    qualis: Optional[str] = None
    magazine: Optional[str] = None


class InstitutionFilter(BaseFilter):
    institution_id: Optional[UUID] = None
    state: Optional[str] = None
    city: Optional[str] = None


class GraduateProgramFilter(BaseFilter):
    institution_id: Optional[UUID] = None
    area: Optional[str] = None
    modality: Optional[str] = None
    rating: Optional[str] = None
