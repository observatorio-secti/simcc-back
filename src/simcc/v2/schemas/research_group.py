"""Schemas de grupo de pesquisa para os endpoints v2."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ResearchGroupRef(BaseModel):
    id: UUID = Field(description='Identificador do grupo')
    name: Optional[str] = Field(None, description='Nome do grupo')
