"""Schemas de programa de pós-graduação para os endpoints v2."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GraduateProgramRef(BaseModel):
    id: UUID = Field(description='Identificador do programa')
    name: str = Field(description='Nome do programa')
    acronym: Optional[str] = Field(None, description='Sigla do programa')
