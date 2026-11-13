# LOTUS — 청년 진로·취업 안내
경험이 부족한 청년이 자신의 관심과 상황을 입력하면 관련 기회, 지원 전 확인 사항,
직무와 준비 활동을 안내하는 서비스입니다. 현재 DB 공고 목록·상세와 규칙 기반 추천 HTTP 연결을 구현했습니다. 운영 배포와 전체 진로 기능은 아직 완료되지 않았습니다.

## 기술과 환경
React 19 + TypeScript 5 + Vite 8 / Python 3.12 + FastAPI + Pydantic / SQLite.
검증 환경: Python 3.12.7, Node 24.18.0, npm 11.16.0. CI도 Python 3.12 / Node 24를 사용합니다.
Python은 venv + pip, 프론트는 npm으로 통일합니다. requirements.txt는 실제 가상환경의 pip freeze,
frontend/package-lock.json은 실제 npm으로 생성했습니다. 설치는 고정된 파일을 사용합니다.
TypeScript 7.0.2는 openapi-typescript 7.13.0의 peer 범위(^5.x)와 충돌하여 5 계열로 변경했습니다.
강제 설치나 legacy-peer-deps는 사용하지 않습니다.

## 설치·실행 (Windows PowerShell, 저장소 루트)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
npm --prefix frontend ci
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```
환경 파일 복사는 최초 한 번만 하며 기존 사용자 설정을 덮어쓰지 않습니다.
별도 터미널에서 `npm --prefix frontend run dev`를 실행합니다. 종료는 각 터미널 Ctrl+C입니다.
프론트: http://localhost:5173 / 서버: http://localhost:8000 / API 문서: http://localhost:8000/docs.
Linux/macOS에서는 `.venv/Scripts/python` 대신 `.venv/bin/python`을 사용합니다.

## 환경변수
backend/settings.py가 저장소 루트 .env를 읽으며 실제 환경변수가 우선합니다.
- CORS_ORIGINS: 쉼표로 구분한 프론트 origin. 기본 http://localhost:5173.
- DATABASE_URL: 기본 sqlite:///runtime/lotus.db. importer와 조회 API가 사용합니다.
- DATA_MODE: demo 또는 real. importer와 조회의 실제·합성 자료 분리용입니다. 공고는 DB에서만 읽으며 요청 중 수집하지 않습니다.
- frontend/.env.local의 VITE_API_BASE_URL: 서버 주소만, 기본 http://localhost:8000.
  /api/v1을 붙이면 오류로 거부합니다. VITE_*는 공개되므로 비밀키를 넣지 않습니다.
외부 AI와 비밀키는 필요하지 않습니다. 프로필 저장 기능도 없습니다.

## 검사·명세 생성
```powershell
.venv\Scripts\python -m pip check
.venv\Scripts\python -m pytest backend/tests tests/integration -q
.venv\Scripts\python -m scripts.validate_examples
.venv\Scripts\python -m scripts.export_openapi
.venv\Scripts\python -m scripts.export_contracts
npm --prefix frontend run generate:types
.venv\Scripts\python -m scripts.check_generated
npm --prefix frontend run check:generated
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
.venv\Scripts\python -m scripts.smoke_servers
```
명세는 실제 모델·라우트에서 생성하고 프론트 타입은 그 OpenAPI에서 생성합니다.
생성 파일을 직접 편집하지 않습니다. smoke_servers는 임시 포트에서 실제 서버 프로세스를 실행하고 종료합니다.
브라우저 렌더링 검사와 실제 서비스 통합 테스트는 별도입니다.

## 현재 구현 상태
health, options, capabilities, CORS, .env 로딩, 공통 오류 응답, 최소 프론트 상태 화면,
공통 모델·검증·날짜 계산·합성 예시·명세/타입 생성이 구현되어 있습니다.
공고 목록·상세와 추천 HTTP API가 DB 자료를 사용합니다. 추천은 기존 태환의 규칙 엔진을 호출하고 원본 공고를 결합합니다. 직무·활동·면접은 미구현으로503, 관련 링크는 조회 구현 후 활성화 검토 대기로503입니다.
유효하지 않은 입력은 422, 알 수 없는 라우트는 404입니다.
미구현을 성공한 빈 목록으로 반환하지 않습니다. 내부 직무·활동·면접 함수는 FeatureUnavailableError를 발생시킵니다.
SQLite importer·공고 조회·데이터 배치·추천 내부 함수·추천 HTTP adapter·화면이 연결됐습니다. 부가 HTTP adapter는 준비했지만 담당 AI 함수 미구현으로 OFF입니다. 외부 AI·배포·서버 검색은 미구현입니다.

## 폴더와 협업
| 폴더 | 담당/용도 |
|---|---|
| frontend | 예원: 화면·API client |
| backend | 건희: 서버·DB·API |
| recommender | 태환: 추천·진로 안내 |
| data_pipeline, data/raw, data/normalized | 시영: 실제 자료 |
| shared, contracts | 공동 모델·규칙·계약·예시 |
| tests/integration | 태환 조율: 연결 검사 |
| runtime | 로컬 DB·로그, Git 제외 |
| docs | 기획·역할·검토·인계 |

[기획](docs/PROJECT.md) · [소유권](docs/OWNERSHIP.md) · [Git 절차](docs/GIT_WORKFLOW.md) ·
[계약](contracts/CONTRACT.md) · [인계·검증 결과](docs/BOOTSTRAP_HANDOFF.md).
팀원은 main 검토·반영 후 docs/tasks/initial의 자기 역할 문서로 시작합니다.

## 실제 공고 DB 준비와 조회
저장소 루트에서 Python3.12 가상환경을 준비한 뒤 다음을 실행합니다.
기존 DB는 지우지 않습니다. 실제 자료 DB와 합성 자료 DB를 같은 파일로 사용하지 않습니다.
```powershell
$env:DATABASE_URL = "sqlite:///runtime/real.db"
$env:DATA_MODE = "real"
.venv\Scripts\python -m backend.importer --input-dir data/normalized
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```
예원 화면을 일반 주소에서 실행합니다. `?preview=1`을 붙이면 별도 예시 응답을 쓰므로 실제 연결 검사가 아닙니다.
화면 입력 확인 → 다음 → 공고 탐색 → 공고 불러오기로 목록을 확인합니다.
관심 공고 저장 후 새로고침하고 관심 공고에서 다시 불러오면 상세 API를 호출합니다.
`opportunities`와 `recommendations`만 활성화돼 있으며 다른 기능은 OFF입니다. DB가 없으면503을 반환하고 자동 생성하지 않습니다.
정상 빈 DB는200 빈 배열, 없는ID는404, 잘못된페이지는422입니다.
목록은 ID 오름차순으로 정렬하고 limit 기본20(1~100), offset 기본0(0 이상)을 사용합니다.
검색·유형 필터는 현재 화면에서 불러온 자료에만 적용됩니다. 서버 검색 파라미터는 없습니다.
실제 자료의 원문·최신성 재확인은 별도이며, DB 조회 성공이 해당 공고의 현재 모집 상태를 보증하지 않습니다.

## 추천과 인계
프로필을 확인하고 다음으로 이동하면 POST /api/v1/recommendations를 호출합니다.
추천은 같은 읽기 전용 DB snapshot의 공고와 시간대가 있는 now를 기존 recommend()에 전달합니다.
서버는 응답 ID·근거·유형·정렬·limit·candidate_count를 검사한 뒤 DB 원본과 결합합니다.
빈 정상 DB나 관련 근거가 없는 자료는200 빈 추천이며, DB 오류는503, 함수 실패·잘못된 내부 결과는500입니다.
현재 real 자료3건과 소프트웨어 관심 입력은 추천0건입니다. 자료의 분야·전공 근거를 임의로 만들지 않습니다.
합성 추천 성공 검사는 별도 demo DB에 contracts/examples를 넣어 실행합니다. real DB와 같은 파일을 쓰지 않습니다.
외부 AI 동의 여부와 관계없이 현재 엔진은 rules이며 외부 API를 호출하지 않습니다.
직무·활동·면접 알고리즘은 태환 담당으로 미구현이며 backend/service_adapters.py의 연결 준비를 성공 구현으로 간주하지 않습니다.
검색 검토안과 담당별 남은 일은 docs/changes/backend-next-steps.md, 인계와 검사는 docs/backend.md를 봅니다.

## 서버 실행 전 DB 점검
자료 입력 후 서버를 켜기 전에 같은 DATABASE_URL/DATA_MODE 환경에서 실행합니다.
```powershell
.venv\Scripts\python -m backend.check_catalog
if ($LASTEXITCODE -ne 0) { throw "DB 점검 실패: 위의 상태 코드와 DB 설정을 확인하세요." }
```
정상이면 status=ok, data_mode와 sources/opportunities/roles/resource_links 개수를 JSON으로 출력합니다.
정상 빈 DB도 ok이며 개수0입니다. 이것이 추천 결과 존재·공고 최신성·전체 서비스 준비 완료를 보장하지는 않습니다.
종료 코드0=정상,1=DB 조회/자료 검증 실패,2=환경 설정 오류,3=예상하지 못한 점검 오류입니다.
실패 시 서버 시작을 멈추는 위 예시는 선택적으로 사용하며 서버의 기존 기동 방식은 바꾸지 않았습니다.
DB 누락·잠금·미지원 스키마·실제/합성 mode 불일치·손상 자료를 검사합니다. DB를 생성·수정하거나 자동 복구하지 않습니다.
오류에는 DB 경로나 자료 원문·환경변수 원문을 출력하지 않습니다. 자세한 정보는 docs/catalog-preflight.md를 봅니다.
