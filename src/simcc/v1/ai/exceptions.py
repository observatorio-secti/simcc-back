from fastapi import HTTPException, status


class AIServiceUnavailableException(HTTPException):
    def __init__(
        self,
        detail: str = 'O serviço de inteligência artificial está temporariamente indisponível ou não configurado.',
    ):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail
        )
