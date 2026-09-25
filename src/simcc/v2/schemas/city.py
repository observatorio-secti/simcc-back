"""Schemas de cidade para os endpoints v2."""

from uuid import UUID

from pydantic import BaseModel, Field


class CityRef(BaseModel):
    id: UUID = Field(description='Identificador da cidade')
    name: str = Field(description='Nome da cidade')
