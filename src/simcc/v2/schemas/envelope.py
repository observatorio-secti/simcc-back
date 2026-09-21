from datetime import datetime
from typing import Any, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationMetadata(BaseModel):
    page: int = Field(..., ge=1, description='Página atual')
    per_page: int = Field(..., ge=1, description='Itens por página')
    total_items: int = Field(
        ..., ge=0, description='Total de itens encontrados'
    )
    total_pages: int = Field(
        ..., ge=0, description='Total de páginas disponíveis'
    )
    has_next: bool = Field(..., description='Indica se existe próxima página')
    has_prev: bool = Field(..., description='Indica se existe página anterior')


class SortMetadata(BaseModel):
    by: str = Field('name', description='Campo de ordenação')
    order: Literal['asc', 'desc'] = Field(
        'asc', description='Sentido da ordenação'
    )


class ResponseMeta(BaseModel):
    took_ms: int = Field(
        ..., description='Tempo de processamento da requisição em ms'
    )
    cached: bool = Field(
        False, description='Indica se resultado veio do cache'
    )
    timestamp: datetime = Field(..., description='Momento da resposta em UTC')


class ResponseEnvelope(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginationMetadata
    filters_applied: dict[str, Any]
    sort: Optional[SortMetadata] = None
    meta: ResponseMeta
    facets: Optional[dict[str, Any]] = None
    summary: Optional[dict[str, Any]] = None
