# 초기 공통 기반 인계 — 2026-11-11 (Asia/Seoul)

## 기준과 보존
- 저장소: https://github.com/kkhee67/LOTUS
- 작업 브랜치: codex/bootstrap (사용자가 기존 브랜치 이어 수정 승인).
- 기준 HEAD: f1997c3c45d4259c2d09d30d5e052df0b069f984. 작업 전 미커밋 변경 없음.
- 확인한 origin/main: 6fcc1821d5ca2c6662313d00ad974e5e86413cac.
- 기존 열린 PR #1 작성자 kkhee67, 기존 python/frontend CI 성공을 실제 조회했다.
- 기존 초안의 사용자 모델·기술 스택·health·capabilities·테스트를 보완했다. 기존 테스트 11개는 보존했다.
- 이전 AI 준비 문서 두 개는 codex/ai/basic-recommendations의 aaf6fc7bba55343ed2d43e20a9d39d1108a7aa0d에 보존되어 있다.
- 다른 팀원의 로컬 작업은 확인할 수 없다. 동시 편집이 없도록 인계를 조율하고 다음 push 전 remote를 다시 확인한다.
- 계약: 실제 존재한 4.0-draft에서 4.1-draft로 보완. 팀 승인 전이다.

## 실제 구현
공통 모델·길이/공백/상호 조건 검증, 출처·공고·근거·OR/예외 표현, 자격증 회차 분리,
순수 날짜 함수, 합성 예시와 데이터셋 참조 검사, 내부 추천/화면 응답 분리,
후속 기능의 타입 있는 미구현 함수, API 계약과 실제 options, 설정·CORS·공통 오류,
최소 프론트 연결 상태, 모델/OpenAPI/TS 생성, CI 설정과 역할별 인계.
데이터 정규화 출력 경로만 예약했고 실제 데이터를 수집하거나 복사하지 않았다.

## 재사용 및 변경점
- Python 3.12.7과 Node 24.18.0/npm 11.16.0에서 검사하고 CI 기준도 3.12/24로 맞췄다.
- 기존 React 19.3.1/Vite 8.3.7 유지. TypeScript 7.0.2는 openapi-typescript 7.13.0과 peer 충돌하여 5.9.3으로 조정.
- 기존 pip 고정 의존성을 유지하고 pydantic-settings/python-dotenv/tzdata 추가 후 실제 pip freeze로 갱신.
- types 생략/[]는 모든 승인 유형. 현재 catalog는 검토 중인 최소 분야 목록이다.
- 모델의 공백 목록·중복 참조·날짜 정합성·근거·출처 코드 검증을 강화했다. 상세는 CONTRACT/FIELDS 참조.
- 기존 docs/backend.md와 TAEHWAN_REVIEW.md는 역사 기록을 보존하고 최신 인계 문서 링크를 추가했다.

## 실행한 명령과 결과
| 명령 | 실제 결과 |
|---|---|
| git fetch origin / git ls-remote --heads origin | 원격 main, AI 브랜치, 기존 bootstrap 확인 |
| gh pr list / gh pr view 1 | 기존 PR 및 해당 커밋 CI 성공 확인 |
| git show origin/codex/bootstrap:각 문서·코드 | 적용 지침·계약·기존 작업 확인 |
| git switch --track origin/codex/bootstrap | 성공, 작업 브랜치 전환 |
| python -m venv .venv | 성공 |
| .venv/Scripts/python -m pip install -r requirements.txt pydantic-settings tzdata | 성공 |
| .venv/Scripts/python -m pip freeze | requirements.txt 갱신 |
| npm ci (frontend) | 기존 잠금 파일 설치 성공 |
| npm install --save-dev --save-exact openapi-typescript | 최초 실패: TypeScript 7과 peer 범위 충돌 |
| npm install --save-dev --save-exact typescript@5 openapi-typescript@7.13.0 | 성공, 실제 package-lock 갱신 |
| python -m pytest backend/tests -q | 초기 기존 검사 11 passed |
| python -m pytest backend/tests tests/integration -q | 첫 수집에서 예약 이름 request 오류, 수정 후 최종 50 passed |
| python -m scripts.validate_examples | 출처1/공고3/직무1/링크1과 요청·응답·참조 검사 통과 |
| python -m scripts.export_openapi / scripts.export_contracts | 실제 모델·라우트 기반 생성 성공 |
| npm run generate:types / check:generated | 생성·현재 명세 일치 통과 |
| npm run typecheck / build | 통과 |
| npm test | 2 passed |
| python -m scripts.smoke_servers | 별도 uvicorn과 Vite HTTP 응답 통과; 생성한 프로세스 종료 |
| python -m scripts.check_generated | OpenAPI/모델 스키마/필드 문서 재생성 일치 |
| python -m pip check | No broken requirements found |
| git check-ignore | .env·DB/WAL·프로필 폴더·venv·node_modules·dist 제외 확인; 두 .env.example은 제외되지 않음 |
| git diff --check | 통과 |

Python 명령은 가상환경 Python으로 실행했다. Starlette TestClient의 AnyIO BlockingPortal deprecated 경고 1개가 남으며 검사를 skip하거나 경고를 숨기지 않았다.
현재 변경의 원격 GitHub Actions는 아직 실행되지 않았다. CI 설정 작성과 과거 PR CI 성공을 현재 변경의 CI 성공으로 간주하지 않는다.
실제 브라우저 렌더링·사용자 입력 E2E·실제 데이터/DB 통합·배포는 미실행이다.

## 실행 가능·미구현과 다음 작업
health/options/capabilities, 최소 프론트 상태 화면과 검증 도구는 실행 가능하다.
목록·상세·링크·개인화 API는 명시적 503이며 내부 AI 함수는 FeatureUnavailableError다.
DB/importer·조회 본개발·실제 수집·추천 계산·완성 UI·외부 AI는 미구현이다.
공통 기반은 로컬 검증된 검토 초안이며 main에 반영되어 팀의 승인 기준이 된 상태는 아니다.

| 담당 | main 검토·반영 후 첫 작업 | 지시문 |
|---|---|---|
| 건희 | 초기화 반복 없이 SQLite importer | tasks/initial/backend.md |
| 예원 | 최소 사용자 프로필 입력 폼 | tasks/initial/frontend.md |
| 시영 | 공개 공식 출처 한 곳 정규화 | tasks/initial/data.md |
| 태환 | 사용자 재개 요청 후 규칙 기반 추천 | tasks/initial/ai.md |

## Git 작업과 PR
로컬 검증 후 사용자가 GitHub 업로드와 팀 인계를 승인했다. 기존 codex/bootstrap에 커밋·push하고 PR #1 설명을 갱신하는 범위로 진행한다. 별도 PR 생성과 main 병합은 포함하지 않는다.
PR 제목·본문은 [PR_DRAFT.md](PR_DRAFT.md)에 준비했다. 이 문서를 팀원에게 메시지로 전송하지 않았다.

## 생성·수정 파일 목록
아래는 이번 로컬 변경 목록이다. 생성된 명세와 타입 파일도 포함한다.

- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `AGENTS.md`
- `README.md`
- `backend/main.py`
- `backend/settings.py`
- `contracts/CONTRACT.md`
- `contracts/FEATURES.json`
- `contracts/FIELDS.md`
- `contracts/INTERNAL_APIS.md`
- `contracts/examples/README.md`
- `contracts/examples/activity_plan.json`
- `contracts/examples/interview_guide.json`
- `contracts/examples/opportunities.json`
- `contracts/examples/recommendation_api_response.json`
- `contracts/examples/recommendation_response.json`
- `contracts/examples/resource_links.json`
- `contracts/examples/role_advice.json`
- `contracts/examples/roles.json`
- `contracts/examples/sources.json`
- `contracts/models.schema.json`
- `contracts/openapi.json`
- `data/normalized/README.md`
- `data_pipeline/README.md`
- `data_pipeline/__init__.py`
- `docs/BOOTSTRAP_HANDOFF.md`
- `docs/GIT_WORKFLOW.md`
- `docs/OWNERSHIP.md`
- `docs/PROJECT.md`
- `docs/PR_DRAFT.md`
- `docs/ROADMAP.md`
- `docs/TAEHWAN_REVIEW.md`
- `docs/backend.md`
- `docs/tasks/initial/ai.md`
- `docs/tasks/initial/backend.md`
- `docs/tasks/initial/data.md`
- `docs/tasks/initial/frontend.md`
- `frontend/.env.example`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/src/api-url.ts`
- `frontend/src/api.ts`
- `frontend/src/generated/api.d.ts`
- `frontend/src/main.tsx`
- `frontend/src/vite-env.d.ts`
- `frontend/tests/api-url.test.ts`
- `recommender/__init__.py`
- `recommender/errors.py`
- `recommender/interviews/__init__.py`
- `recommender/interviews/service.py`
- `recommender/opportunities/__init__.py`
- `recommender/opportunities/service.py`
- `recommender/roadmap/__init__.py`
- `recommender/roadmap/service.py`
- `recommender/roles/__init__.py`
- `recommender/roles/service.py`
- `requirements.txt`
- `scripts/check_generated.py`
- `scripts/export_contracts.py`
- `scripts/smoke_servers.py`
- `scripts/validate_examples.py`
- `shared/catalog.json`
- `shared/models/__init__.py`
- `shared/rules.py`
- `shared/validation.py`
- `tests/integration/test_contracts.py`
