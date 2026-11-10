import os
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from shared.models import RecommendationRequest

FEATURES = ("recommendations", "career-roles", "activity-plan", "interview-guide")
app = FastAPI(title="LOTUS bootstrap draft", version="4.0-draft")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

def error(status, code, message):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": []}})

@app.exception_handler(RequestValidationError)
async def invalid(request: Request, exc: RequestValidationError):
    return error(422, "VALIDATION_ERROR", "입력 형식을 확인해 주세요")

@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return error(exc.status_code, "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR", "요청을 처리할 수 없습니다")

@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    return error(500, "INTERNAL_ERROR", "서버 오류가 발생했습니다")

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "contract_version": "4.0-draft"}

@app.get("/api/v1/capabilities")
def capabilities():
    return {name: {"enabled": False, "implemented": False, "unavailable_reason": "초기 초안: 미구현"} for name in FEATURES}

@app.post("/api/v1/recommendations")
def recommendations(request: RecommendationRequest):
    return error(503, "FEATURE_UNAVAILABLE", "아직 구현되지 않은 기능입니다")

def unavailable():
    return error(503, "FEATURE_UNAVAILABLE", "아직 구현되지 않은 기능입니다")

for feature in FEATURES:
    if feature != "recommendations":
        app.add_api_route(f"/api/v1/{feature}", unavailable, methods=["POST"], name=feature)
