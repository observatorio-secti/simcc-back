"""Schemas para os endpoints de catálogo de filtros."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from simcc.v2.schemas.researcher import Pagination


class CatalogItem(BaseModel):
    id: UUID = Field(description='Identificador do recurso')
    name: str = Field(description='Nome do recurso')
    acronym: Optional[str] = Field(None, description='Sigla do recurso')


class CatalogResponse(BaseModel):
    data: list[CatalogItem] = Field(description='Lista de itens do catálogo')
    pagination: Pagination = Field(description='Metadados de paginação')
