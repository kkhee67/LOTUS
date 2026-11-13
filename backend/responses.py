"""Single public error envelope; callers supply only safe fixed messages."""
from fastapi.responses import JSONResponse
from shared.models import ErrorBody, ErrorResponse


def error_response(status: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status, content=payload.model_dump(mode='json'))
