"""Envelopes comuns das respostas v2: meta, detalhe e erro."""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T')


class Meta(BaseModel):
    took_ms: int = Field(description='Tempo de processamento em milissegundos')
    cached: bool = Field(description='Se a resposta veio do cache')
    timestamp: datetime = Field(description='Momento da resposta (UTC)')
    data_as_of: Optional[datetime] = Field(
        None,
        description=(
            'Última atualização dos dados de busca (refresh das visões '
            'materializadas)'
        ),
    )


class DetailResponse(BaseModel, Generic[T]):
    """Resposta de detalhe: um objeto em `data` e os metadados."""

    data: T
    meta: Meta


class ErrorDetail(BaseModel):
    field: Optional[str] = Field(
        None, description='Parâmetro ou campo relacionado ao erro'
    )
    message: str = Field(description='Descrição do problema')
    type: Optional[str] = Field(None, description='Tipo do erro de validação')
    input: Optional[Any] = Field(None, description='Valor recebido')


class ErrorBody(BaseModel):
    code: str = Field(
        description=(
            'Código estável do erro (ex.: not_found, validation_error, '
            'unknown_parameter)'
        )
    )
    message: str = Field(description='Mensagem legível')
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {'model': ErrorResponse, 'description': 'Recurso não encontrado'},
    422: {'model': ErrorResponse, 'description': 'Parâmetros inválidos'},
}
LIST_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: ERROR_RESPONSES[422],
}
