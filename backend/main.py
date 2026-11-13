from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from pydantic import TypeAdapter
from backend.settings import ROOT, Settings
from backend.opportunity_query import create_opportunity_router
from backend.service_adapters import create_service_router
from shared.models import Capability, ErrorBody, ErrorResponse, HealthResponse, OptionsResponse
from shared.rules import CONTRACT_VERSION

FEATURES = ('recommendations', 'career-roles', 'activity-plan', 'interview-guide')
CAPABILITY_NAMES = (*FEATURES, 'opportunities', 'resource-links')
IMPLEMENTED_FEATURES = {'opportunities', 'recommendations', 'resource-links'}
settings = Settings()
options = OptionsResponse.model_validate_json((ROOT / 'shared/catalog.json').read_text(encoding='utf-8'))
capability_flags = TypeAdapter(dict[str, Capability]).validate_json((ROOT / 'contracts/FEATURES.json').read_text(encoding='utf-8'))
def validate_capability_flags(flags):
    if set(flags) != set(CAPABILITY_NAMES):
        raise RuntimeError('Capability names must match supported features')
    for name, flag in flags.items():
        if flag.implemented != (name in IMPLEMENTED_FEATURES):
            raise RuntimeError('Capability implementation must match server code')
        if flag.enabled and (not flag.implemented or flag.unavailable_reason is not None):
            raise RuntimeError('Enabled capabilities must be implemented and available')
        if not flag.enabled and not flag.unavailable_reason:
            raise RuntimeError('Disabled capabilities need an unavailable reason')

validate_capability_flags(capability_flags)

ERRORS = {code: {'model': ErrorResponse} for code in (404, 422, 500, 503)}
app = FastAPI(title='LOTUS bootstrap draft', version=CONTRACT_VERSION, responses=ERRORS)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

def error(status: int, code: str, message: str):
    payload = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status, content=payload.model_dump(mode='json'))

@app.exception_handler(RequestValidationError)
async def invalid(request: Request, exc: RequestValidationError):
    return error(422, 'VALIDATION_ERROR', '입력 형식을 확인해 주세요')

@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return error(exc.status_code, 'NOT_FOUND' if exc.status_code == 404 else 'HTTP_ERROR', '요청을 처리할 수 없습니다')

@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    return error(500, 'INTERNAL_ERROR', '서버 오류가 발생했습니다')

@app.get('/api/v1/health', response_model=HealthResponse)
def health():
    return HealthResponse(status='ok', contract_version=CONTRACT_VERSION)

@app.get('/api/v1/options', response_model=OptionsResponse)
def get_options():
    return options

@app.get('/api/v1/capabilities', response_model=dict[str, Capability])
def capabilities():
    return capability_flags

app.include_router(create_opportunity_router(
    settings,
    enabled=lambda: capability_flags['opportunities'].enabled
                    and capability_flags['opportunities'].implemented,
))

app.include_router(create_service_router(
    settings,
    enabled=lambda name: capability_flags[name].enabled and capability_flags[name].implemented,
))
