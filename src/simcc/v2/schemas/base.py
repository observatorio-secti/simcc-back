"""Model base das respostas v2."""

import types
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, model_validator

# Valores que o banco usa para "sem valor" e que a API devolve como null
EMPTY_VALUES = frozenset({'', 'None', 'none', 'null', 'NULL'})


def _accepts_none(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        return type(None) in get_args(annotation)
    return annotation is type(None)


class V2Model(BaseModel):
    """Base dos schemas de resposta v2.

    Campos que aceitam `null` nunca saem como string vazia ou `"None"`:
    esses valores viram `null` na validação.
    """

    @model_validator(mode='before')
    @classmethod
    def _empty_to_none(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        cleaned = None
        for name, field in cls.model_fields.items():
            key = name if name in data else field.alias
            if key is None or key not in data:
                continue
            value = data[key]
            if (
                isinstance(value, str)
                and value.strip() in EMPTY_VALUES
                and _accepts_none(field.annotation)
            ):
                if cleaned is None:
                    cleaned = dict(data)
                cleaned[key] = None
        return data if cleaned is None else cleaned
