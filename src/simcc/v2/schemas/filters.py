from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class BaseFilter(BaseModel):
    q: Optional[str] = Field(None, description='Termo de busca textual')


class BaseTemporalFilter(BaseFilter):
    year_start: Optional[int] = Field(
        None, description='Ano inicial do intervalo temporal'
    )
    year_end: Optional[int] = Field(
        None, description='Ano final do intervalo temporal'
    )


class ResearcherFilter(BaseTemporalFilter):
    model_config = ConfigDict(extra='forbid')

    q: Optional[str] = Field(
        None, description='Termo de busca por nome do pesquisador'
    )
    year_start: Optional[int] = Field(
        None, description='Ano inicial de produção bibliográfica'
    )
    year_end: Optional[int] = Field(
        None, description='Ano final de produção bibliográfica'
    )
    institution_id: list[UUID] = Field(
        default=[],
        description='IDs das instituições de vínculo',
    )
    graduate_program_id: list[UUID] = Field(
        default=[],
        description='IDs dos programas de pós-graduação',
    )

    @field_validator('institution_id', 'graduate_program_id', mode='before')
    @classmethod
    def _coerce_uuid_list(cls, value: Any) -> list[UUID]:
        if not value:
            return []
        if isinstance(value, (str, UUID)):
            return [UUID(str(value))]
        if isinstance(value, (list, tuple, set)):
            return [UUID(str(item)) for item in value if item]
        return []

    @model_validator(mode='before')
    @classmethod
    def _ignore_pagination_and_sort_params(cls, data: Any) -> Any:
        if isinstance(data, dict):
            endpoint_params = {
                'page',
                'per_page',
                'sort_by',
                'sort_order',
                'facets',
                'include',
                'matches_limit',
            }
            return {k: v for k, v in data.items() if k not in endpoint_params}
        return data

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


KNOWN_RESEARCHER_PARAMS = {
    'q',
    'year_start',
    'year_end',
    'institution_id',
    'graduate_program_id',
    'page',
    'per_page',
    'sort_by',
    'sort_order',
    'facets',
    'include',
    'matches_limit',
}


def validate_unknown_researcher_params(request: Request) -> None:
    """Valida se há parâmetros desconhecidos na query string."""
    for param_name in request.query_params:
        if param_name not in KNOWN_RESEARCHER_PARAMS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Parâmetro desconhecido: '{param_name}'",
            )


def get_researcher_filter(
    *,
    q: Optional[str] = Query(None, description='Termo de busca textual'),
    year_start: Optional[int] = Query(
        None, description='Ano inicial de produção bibliográfica'
    ),
    year_end: Optional[int] = Query(
        None, description='Ano final de produção bibliográfica'
    ),
    institution_id: list[UUID] = Query(
        default=[],
        description='IDs das instituições de vínculo',
    ),
    graduate_program_id: list[UUID] = Query(
        default=[],
        description='IDs dos programas de pós-graduação',
    ),
) -> ResearcherFilter:
    """Extrai filtros de pesquisador dos parâmetros de query string."""
    try:
        return ResearcherFilter(
            q=q,
            year_start=year_start,
            year_end=year_end,
            institution_id=institution_id,
            graduate_program_id=graduate_program_id,
        )
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(err.errors()),
        ) from err


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
