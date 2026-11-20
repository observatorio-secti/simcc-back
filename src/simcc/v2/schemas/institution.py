"""Schemas de instituição compartilhados entre os endpoints v2."""

from typing import Any, Mapping, Optional
from uuid import UUID

from pydantic import Field

from simcc.core.utils import (
    get_institution_cover_url,
    get_institution_logo_url,
)
from simcc.v2.schemas.base import V2Model


class InstitutionRef(V2Model):
    id: UUID = Field(description='Identificador da instituição')
    name: str = Field(description='Nome da instituição')
    acronym: Optional[str] = Field(None, description='Sigla da instituição')
    image: Optional[str] = Field(None, description='URL do logo')
    cover: Optional[str] = Field(None, description='URL da imagem de capa')

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> 'InstitutionRef':
        """Monta a referência resolvendo logo e capa a partir da sigla.

        O logo em disco tem prioridade sobre a coluna `institution.image`.
        """
        acronym = row['acronym']
        return cls(
            id=row['id'],
            name=row['name'],
            acronym=acronym,
            image=get_institution_logo_url(acronym) or row['image'],
            cover=get_institution_cover_url(acronym),
        )
