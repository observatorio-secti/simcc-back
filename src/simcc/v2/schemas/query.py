"""Transforma models Pydantic em dependências de query string."""

import inspect
from typing import Any, Callable, TypeVar

from fastapi import Query
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

ModelT = TypeVar('ModelT', bound=BaseModel)


def as_query(model: type[ModelT]) -> Callable[..., ModelT]:
    """Dependência que lê cada campo de `model` como um parâmetro de query.

    O model continua sendo a única declaração: nome, tipo, padrão e
    descrição de cada parâmetro vêm dos seus `Field`s, e aparecem no
    OpenAPI um a um. Erros de validação do model (inclusive de
    `model_validator`) viram HTTP 422.
    """
    parameters = [
        inspect.Parameter(
            name,
            inspect.Parameter.KEYWORD_ONLY,
            annotation=field.annotation,
            default=Query(
                field.get_default(call_default_factory=True),
                description=field.description,
            ),
        )
        for name, field in model.model_fields.items()
    ]

    def dependency(**values: Any) -> ModelT:
        try:
            return model(**values)
        except ValidationError as err:
            raise RequestValidationError(err.errors()) from err

    dependency.__signature__ = inspect.Signature(parameters)
    dependency.__name__ = f'{model.__name__}_query'
    return dependency
