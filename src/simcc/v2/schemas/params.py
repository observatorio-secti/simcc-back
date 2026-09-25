from typing import Any, Literal, Optional

from fastapi import HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description='Número da página')
    per_page: int = Field(20, ge=1, le=100, description='Itens por página')


class SortParams(BaseModel):
    sort_by: Literal['name', 'id', 'relevance'] = Field(
        'name', description='Campo para ordenação'
    )
    sort_order: Optional[Literal['asc', 'desc']] = Field(
        None, description='Direção da ordenação (asc/desc)'
    )

    @model_validator(mode='after')
    def set_default_sort_order(self) -> 'SortParams':
        if self.sort_order is None:
            self.sort_order = 'desc' if self.sort_by == 'relevance' else 'asc'
        return self


ALLOWED_FACETS = {'institution', 'graduate_program', 'year', 'source_type'}
ALLOWED_INCLUDES = {'matches'}


class SearchOptions(BaseModel):
    facets: list[str] = Field(
        default=[],
        description=(
            'Lista de facets opt-in (institution, graduate_program, '
            'year, source_type)'
        ),
    )
    include: list[str] = Field(
        default=[],
        description='Recursos adicionais opt-in (ex.: matches)',
    )
    matches_limit: int = Field(
        3,
        ge=1,
        le=5,
        description='Número máximo de evidências por pesquisador',
    )

    @field_validator('facets', 'include', mode='before')
    @classmethod
    def _split_comma_separated(cls, v: Any) -> list[str]:
        if not v or type(v).__name__ == '_HAS_DEFAULT_FACTORY_CLASS':
            return []
        if isinstance(v, str):
            return [part.strip() for part in v.split(',') if part.strip()]
        if isinstance(v, (list, tuple, set)):
            result = []
            for item in v:
                if isinstance(item, str):
                    result.extend([
                        p.strip() for p in item.split(',') if p.strip()
                    ])
                elif item:
                    result.append(str(item))
            return result
        return []

    @field_validator('facets', mode='after')
    @classmethod
    def _validate_facets(cls, v: list[str]) -> list[str]:
        invalid = [f for f in v if f not in ALLOWED_FACETS]
        if invalid:
            raise ValueError(
                f'Facets desconhecidos: {invalid}. '
                f'Permitidos: {sorted(ALLOWED_FACETS)}'
            )
        return v

    @field_validator('include', mode='after')
    @classmethod
    def _validate_include(cls, v: list[str]) -> list[str]:
        invalid = [inc for inc in v if inc not in ALLOWED_INCLUDES]
        if invalid:
            raise ValueError(
                f'Includes desconhecidos: {invalid}. '
                f'Permitidos: {sorted(ALLOWED_INCLUDES)}'
            )
        return v


def get_search_options(
    facets: list[str] = Query(
        default=[],
        description=(
            'Lista de facets opt-in (institution, graduate_program, '
            'year, source_type)'
        ),
    ),
    include: list[str] = Query(
        default=[],
        description='Recursos adicionais opt-in (ex.: matches)',
    ),
    matches_limit: int = Query(
        3,
        ge=1,
        le=5,
        description='Número máximo de evidências por pesquisador',
    ),
) -> SearchOptions:
    """Extrai opções de busca de parâmetros de query string."""
    try:
        return SearchOptions(
            facets=facets,
            include=include,
            matches_limit=matches_limit,
        )
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(err.errors()),
        ) from err
