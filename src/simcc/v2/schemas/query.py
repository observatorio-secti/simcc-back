"""Transforma models Pydantic em dependências de query string."""

import inspect
from typing import Any, Callable, TypeVar

from fastapi import Query, Request
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
    aliases = query_aliases(model)
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
    if aliases:
        parameters.append(
            inspect.Parameter(
                'request__',
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Request,
            )
        )

    def dependency(**values: Any) -> ModelT:
        request: Request | None = values.pop('request__', None)
        if request is not None:
            params = request.query_params
            for alias, field in aliases.items():
                if field not in params and alias in params:
                    values[field] = params[alias]
        try:
            return model(**values)
        except ValidationError as err:
            raise RequestValidationError(err.errors()) from err

    dependency.__signature__ = inspect.Signature(parameters)
    dependency.__name__ = f'{model.__name__}_query'
    return dependency


def query_aliases(model: type[BaseModel]) -> dict[str, str]:
    """Nomes antigos aceitos na query (`QUERY_ALIASES` do model):
    `{alias: campo}`. Não aparecem no OpenAPI."""
    return dict(getattr(model, 'QUERY_ALIASES', {}) or {})


def known_param_names(*models: type[BaseModel]) -> frozenset[str]:
    """Nomes aceitos na query: campos e aliases declarados."""
    names: set[str] = set()
    for model in models:
        names.update(model.model_fields)
        names.update(query_aliases(model))
    return frozenset(names)


def forbid_unknown_params(
    *models: type[BaseModel],
) -> Callable[[Request], None]:
    """Dependência que devolve 422 para parâmetros de query fora dos
    campos de `models`."""
    from simcc.v2.errors import unknown_parameter  # noqa: PLC0415

    known = known_param_names(*models)

    def dependency(request: Request) -> None:
        for param_name in request.query_params:
            if param_name not in known:
                raise unknown_parameter(param_name)

    return dependency
