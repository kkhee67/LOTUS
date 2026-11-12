import json
from typing import Annotated
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from pydantic import TypeAdapter
from backend.settings import ROOT, Settings
from shared.models import (
    ActivityPlanRequest, ActivityPlanResponse, Capability, ErrorBody, ErrorResponse,
    HealthResponse, InterviewGuideRequest, InterviewGuideResponse, Opportunity,
    OptionsResponse, Page, RecommendationApiResponse, RecommendationRequest,
    ResourceLink, RoleAdviceRequest, RoleAdviceResponse,
)
from shared.rules import CONTRACT_VERSION

FEATURES = ('recommendations', 'career-roles', 'activity-plan', 'interview-guide')
UNIMPLEMENTED = (*FEATURES, 'opportunities', 'resource-links')
settings = Settings()
options = OptionsResponse.model_validate_json((ROOT / 'shared/catalog.json').read_text(encoding='utf-8'))
capability_flags = TypeAdapter(dict[str, Capability]).validate_json((ROOT / 'contracts/FEATURES.json').read_text(encoding='utf-8'))
if set(capability_flags) != set(UNIMPLEMENTED) or any(x.enabled or x.implemented for x in capability_flags.values()):
    raise RuntimeError('Bootstrap capabilities must match unavailable implementations')

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

def unavailable():
    return error(503, 'FEATURE_UNAVAILABLE', '아직 구현되지 않은 기능입니다')

@app.get('/api/v1/health', response_model=HealthResponse)
def health():
    return HealthResponse(status='ok', contract_version=CONTRACT_VERSION)

@app.get('/api/v1/options', response_model=OptionsResponse)
def get_options():
    return options

@app.get('/api/v1/capabilities', response_model=dict[str, Capability])
def capabilities():
    return capability_flags

@app.get('/api/v1/opportunities', response_model=Page[Opportunity])
def opportunities(limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0):
    return unavailable()

@app.get('/api/v1/opportunities/{id}', response_model=Opportunity)
def opportunity(id: str):
    return unavailable()

@app.get('/api/v1/resource-links', response_model=Page[ResourceLink])
def resource_links(limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0):
    return unavailable()

@app.post('/api/v1/recommendations', response_model=RecommendationApiResponse)
def recommendations(request: RecommendationRequest):
    return unavailable()

@app.post('/api/v1/career-roles', response_model=RoleAdviceResponse)
def career_roles(request: RoleAdviceRequest):
    return unavailable()

@app.post('/api/v1/activity-plan', response_model=ActivityPlanResponse)
def activity_plan(request: ActivityPlanRequest):
    return unavailable()

@app.post('/api/v1/interview-guide', response_model=InterviewGuideResponse)
def interview_guide(request: InterviewGuideRequest):
    return unavailable()
