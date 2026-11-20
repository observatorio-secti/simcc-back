"""Formato único de erro da v2: `{ error: { code, message, details[] } }`."""

import logging
from http import HTTPStatus
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from simcc.v2.schemas.envelope import ErrorBody, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

STATUS_CODES = {
    400: 'bad_request',
    401: 'unauthorized',
    403: 'forbidden',
    404: 'not_found',
    405: 'method_not_allowed',
    409: 'conflict',
    422: 'validation_error',
    429: 'too_many_requests',
    500: 'internal_error',
    502: 'bad_gateway',
    503: 'service_unavailable',
}


class ApiError(HTTPException):
    """`HTTPException` com código de erro estável e detalhes opcionais."""

    def __init__(
        self,
        status_code: int,
        message: str,
        code: Optional[str] = None,
        details: Optional[list[ErrorDetail]] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code or STATUS_CODES.get(status_code, 'error')
        self.details = details or []


def unknown_parameter(name: str) -> ApiError:
    return ApiError(
        status_code=HTTPStatus.UNPROCESSABLE_CONTENT,
        message=f"Parâmetro desconhecido: '{name}'",
        code='unknown_parameter',
        details=[
            ErrorDetail(
                field=name,
                message='Parâmetro não aceito por esta rota',
                type='unknown_parameter',
            )
        ],
    )


def _response(status_code: int, body: ErrorBody) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(ErrorResponse(error=body)),
    )


def _details_from_validation(
    errors: list[dict[str, Any]],
) -> list[ErrorDetail]:
    details = []
    for err in errors:
        loc = [str(part) for part in err.get('loc', ()) if part != 'query']
        details.append(
            ErrorDetail(
                field='.'.join(loc) or None,
                message=str(err.get('msg', '')),
                type=err.get('type'),
                input=jsonable_encoder(err.get('input')),
            )
        )
    return details


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    if isinstance(exc, ApiError):
        body = ErrorBody(
            code=exc.code, message=str(exc.detail), details=exc.details
        )
    elif isinstance(exc.detail, list):
        body = ErrorBody(
            code=STATUS_CODES.get(exc.status_code, 'error'),
            message='Parâmetros inválidos',
            details=_details_from_validation(exc.detail),
        )
    else:
        body = ErrorBody(
            code=STATUS_CODES.get(exc.status_code, 'error'),
            message=str(exc.detail),
        )
    return _response(exc.status_code, body)


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _response(
        HTTPStatus.UNPROCESSABLE_CONTENT,
        ErrorBody(
            code='validation_error',
            message='Parâmetros inválidos',
            details=_details_from_validation(list(exc.errors())),
        ),
    )


async def _unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception('Erro não tratado em %s', request.url.path)
    return _response(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        ErrorBody(code='internal_error', message='Erro interno do servidor'),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(
        RequestValidationError, _validation_exception_handler
    )
    app.add_exception_handler(Exception, _unhandled_exception_handler)
