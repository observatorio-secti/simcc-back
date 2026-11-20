"""Schemas para o endpoint de sugestão de termos v2."""

from pydantic import BaseModel, Field, field_validator

from simcc.v2.schemas.kinds import (
    DictionaryType,
    DictionaryTypeParam,
    normalize_kind_list,
)
from simcc.v2.schemas.researcher import Meta


class SuggestionParams(BaseModel):
    q: str = Field(
        min_length=1,
        max_length=100,
        description=(
            'Início do termo digitado. Ignora acentuação e '
            'maiúsculas/minúsculas'
        ),
    )
    source_type: list[DictionaryTypeParam] = Field(
        default_factory=list,
        description=(
            'Dicionários considerados. Sem valor, considera todos e soma '
            'as frequências do termo'
        ),
    )
    limit: int = Field(
        10, ge=1, le=100, description='Quantidade máxima de sugestões'
    )

    @field_validator('source_type', mode='before')
    @classmethod
    def _normalize_source_type(cls, v):
        return normalize_kind_list(v)

    @field_validator('q', mode='before')
    @classmethod
    def _strip_q(cls, v):
        return v.strip() if isinstance(v, str) else v


class Suggestion(BaseModel):
    term: str = Field(description='Termo sugerido')
    frequency: int = Field(
        description='Quantidade de textos em que o termo aparece'
    )
    source_types: list[DictionaryType] = Field(
        default_factory=list,
        description='Dicionários de origem onde o termo ocorre',
    )


class SuggestionResponse(BaseModel):
    data: list[Suggestion] = Field(
        description='Sugestões, da mais para a menos frequente'
    )
    meta: Meta
