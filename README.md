# LOTUS — 초기 검토 초안
React + TypeScript + Vite / Python 3.11 + FastAPI + Pydantic / SQLite(후속 구현).
현재 초안은 팀 승인 전이며 다른 담당 개발 시작 기준이 아니다.

## 설치와 실행 (저장소 루트)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
다른 터미널에서:
```powershell
cd frontend
npm ci
npm run dev
```
프론트 http://localhost:5173 / 서버 http://localhost:8000 / API 문서 /docs.
종료는 각 터미널 Ctrl+C. 기본 설정은 코드에서 제공하며 .env는 자동 로딩하지 않는다.
필요 시 PowerShell `$env:CORS_ORIGINS='http://localhost:5173'`으로 설정한다.
VITE_API_BASE_URL은 향후 client에서 서버 주소만 받으며 /api/v1을 넣지 않는다. 현재 프론트 client는 미구현이다.

## 검사
```powershell
.venv\Scripts\python -m pytest backend/tests
.venv\Scripts\python -m scripts.export_openapi
cd frontend
npm run typecheck
npm run build
```
health·capabilities는 구현, 개인화 API는 503 FEATURE_UNAVAILABLE. DB·자료 입력·추천·부가 기능은 미구현이다.
정식 계약 전체·생성 TS 타입·전체 예시 참조 검증·프론트 테스트은 후속 보완이다.
규격: contracts/CONTRACT.md / 역할: docs/OWNERSHIP.md / 절차: docs/GIT_WORKFLOW.md.
검토 요청: docs/TAEHWAN_REVIEW.md / 검사 결과·미완료: docs/backend.md.
