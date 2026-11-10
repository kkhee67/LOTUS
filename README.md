# LOTUS — 초기 검토 초안
React + TypeScript + Vite / Python 3.11 + FastAPI + Pydantic / SQLite(후속 구현).
현재 초안은 팀 승인 전이며 다른 담당 개발 시작 기준이 아니다.

## 팀 역할 (검토 초안)

| 담당 | 맡은 일 |
|---|---|
| 예원 · 프론트엔드 | 사용자 화면과 화면의 API 연결 |
| 백엔드 담당 | 초기 공통 프로젝트, 서버, DB, API 구현 |
| 시영 · 데이터 | 실제 공고·자격증·직무·학교 공지 수집과 검증 |
| 태환 · AI 및 전체 통합 | 추천·진로 안내 개발, 전체 연결·검증과 조율 |

각 담당은 자신의 기능과 테스트를 책임집니다. 공통 API·데이터 형식·설정 변경은 태환이 관련 담당자와 조율하고 별도 PR로 검토합니다.
모든 변경은 다른 팀원이 검토하며 최종 병합은 사람이 진행합니다.

**[상세 역할과 수정 범위 보기](docs/OWNERSHIP.md)** · [협업 지침](AGENTS.md) · [Git 작업 절차](docs/GIT_WORKFLOW.md)

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
