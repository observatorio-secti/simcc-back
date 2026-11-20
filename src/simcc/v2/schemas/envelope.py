"""Envelopes comuns das respostas v2: meta, detalhe e erro."""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar('T')


class Meta(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'took_ms': 42,
                    'cached': False,
                    'timestamp': '2026-11-20T14:00:00Z',
                    'data_as_of': '2026-11-20T03:00:00Z',
                }
            ]
        }
    )

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
    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'error': {
                        'code': 'unknown_parameter',
                        'message': "Parâmetro desconhecido: 'foo'",
                        'details': [
                            {
                                'field': 'foo',
                                'message': 'Parâmetro não aceito por esta '
                                'rota',
                                'type': 'unknown_parameter',
                                'input': None,
                            }
                        ],
                    }
                },
                {
                    'error': {
                        'code': 'not_found',
                        'message': 'Pesquisador não encontrado.',
                        'details': [],
                    }
                },
            ]
        }
    )

    error: ErrorBody


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {'model': ErrorResponse, 'description': 'Recurso não encontrado'},
    422: {'model': ErrorResponse, 'description': 'Parâmetros inválidos'},
}
LIST_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: ERROR_RESPONSES[422],
}
