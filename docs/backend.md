# 추천 HTTP 연결·기능 활성화 검증 — 2026-11-13

## 기준과 구현
기준: 공고 조회 PR #7의8c831f2e49b092674ff3813319efee5759937b48. main7fc193f는 변경하지 않았다.
사용자가 전달한 태환의 조건부 승인을 따라 DB→추천→화면을 검증한 뒤 recommendations를 true/true로 전환했다.
opportunities와 recommendations만 ON. resource-links는 DB 조회 구현(implemented=true) 후 OFF로 검토 대기다.
직무·활동·면접은 함수 미구현이므로 false/false다. 기존 AI 알고리즘과 프론트 기능은 수정하지 않았다.

## 코드가 하는 일과 막는 오류
1. read_catalog: importer가 만든 SQLite를 읽기 전용 snapshot으로 검증한다. 파일 생성·DB 쓰기를 하지 않는다.
   스키마·mode·ID·출처 관계·모델이 틀리면503. real/synthetic 혼합과 손상 자료의 정상 응답을 막는다.
2. assemble_recommendations: 공고와 프로필 복사본, aware now를 기존 recommend에 넘긴다.
   결과 모델을 재검증하고 ID·근거·허용 유형·중복·정렬·limit·candidate_count를 확인한다.
   DB 원본을 ID로 결합하므로 엔진이 복사본의 제목을 바꿔도 화면 원본은 변하지 않는다.
   동의 없는 LLM 표시를 거부하며 기존 rules 엔진은 외부 호출을 하지 않는다.
3. create_service_router: 정상 추천/빈 결과200, DB·미구현 오류503, 잘못된 내부 결과/함수 실패500으로 구분한다.
   예외 원문을 응답하거나 기록하지 않는다. 개인정보가 URL이나 DB에 저장되는 경로를 추가하지 않았다.
4. validate_guidance: 직무 출처/ID, 계획 공고ID, 면접 경험ID를 확인한다. 실제 AI 함수 미구현을 대체하지 않는다.
5. FEATURES/registry: 구현 사실과 노출 상태를 구분한다. 미구현 기능을 켜면 기동을 거부한다.

## 실제 검사
환경: 기존 Python3.12.7 고정 의존성 가상환경, Node24.18/npm11.16.
```powershell
# 이 검토 폴더에서 사용한 실제 Python 경로
../importer-review/.venv/Scripts/python.exe -m pytest data_pipeline/tests backend/tests tests/integration -q --basetemp <이번 실행의 임시 경로> -o cache_dir=<이번 실행의 캐시 경로>
../importer-review/.venv/Scripts/python.exe -m scripts.validate_examples
../importer-review/.venv/Scripts/python.exe -m data_pipeline.normalize --validate-only
../importer-review/.venv/Scripts/python.exe -m scripts.export_openapi
../importer-review/.venv/Scripts/python.exe -m scripts.export_contracts
../importer-review/.venv/Scripts/python.exe -m scripts.check_generated
../importer-review/.venv/Scripts/python.exe -m pip check
npm --prefix frontend ci --cache ../npm-cache --no-audit --no-fund
npm --prefix frontend run generate:types
npm --prefix frontend run check:generated
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
../importer-review/.venv/Scripts/python.exe -m scripts.smoke_servers
git diff --check
```
최종 Python268 passed/기존AnyIO 경고1/18.34s, 신규adapter42건 포함. 프론트24 passed, 나머지 명령 모두 통과.
초기 pytest의 상대 cache 경로가 환경에서 거부돼 절대 경로로 재실행했다. 코드 실패가 아닌 실행환경 문제였다.
첫 보조 UI 스크립트는 httpx 없는 전역Python을 선택해 실패했고 기존venv로 실행해 정상화했다.
원본/생성 OpenAPI의 components.schemas와 경로 집합이 같은 것을 비교했다. 라우터 등록에 따른 순서·오류 설명 변경은 재생성했다.

신규 검사는 정상/빈 추천, 실제 DB0건, 잠금·누락·mode·손상, 기능OFF 전DB비접근,
없는ID·근거·유형·개수·순서·중복·부적격·동의없는LLM·엔진 예외 거부, 원본 불변,
정확한 마감 직전/정각과 날짜 마감, 미확인 자격의 '확인 필요', 관련 링크 페이지,
후속 함수 미구현503·잘못된참조500·없는요청참조404·실패 독립성 등을 확인한다.
테스트 더블은 잘못된 엔진 출력/미래 함수 참조 검사에만 사용했다. 정상 추천은 실제 recommend 함수다.

## 실제 화면과 HTTP
preview=1이나 API응답 대체를 쓰지 않았다. 임시DB2개와 로컬 API/Vite 프로세스를 별도로 실행했다.
- real: normalized3건 입력, 소프트웨어 관심으로 실제 POST200/추천0건과 화면 빈 안내 확인.
- demo: contracts/examples를 별도 DB에 입력, 실제 POST200/추천1건/40점/추가확인필요/합성표시 확인.
- 화면 확인 시에만 임시 서버 프로세스의 추천 플래그를 ON으로 두었고 검증 성공 후 저장소 플래그를 ON으로 바꿨다.
- 기능 활성화 후 전체Python검사와 실제 서버 기동 smoke를 다시 통과했다.
- 프로필은 합성 관심 분야만 입력했다. 운영 DB나 실제 개인정보로 실험하지 않았다.
- 생성한 서버는 모두 종료했다. 화면 증거는 outputs의 recommendation-real-empty-ui.jpg와 recommendation-synthetic-success-ui.jpg다.

## 완료와 미완료
기본 backend1차: 공통기반, importer, 목록·상세, 기본추천HTTP와 원본결합, 오류/기능게이트 검사와 인계 완료.
긍정적인 실제 공고 추천 한 건은 미완료다. real3건은 분야·전공 근거가 부족해 소프트웨어 추천0건이며 자료 보강이 필요하다.
직무·활동·면접의 backend adapter는 준비했지만 태환의 실제 함수와 real 직무자료가 없어 기능완료가 아니다.
서버검색은 docs/changes/backend-next-steps.md의 별도 검토안이다. q/types 파라미터를 미리 추가하지 않았다.
대량성능/운영DB/외부배포/외부원문 최신성/네명 초대 수락은 미검증이다. 매 요청 전체catalog 검증 비용도 남아 있다.
공고 조회 PR #7은 원격CI success를 확인했다. 이번 신규 PR의 CI는 업로드 후 따로 확인한다.
작성자 외 검토·사람의 병합은 남았다. 다른 팀원의 작업/회의/승인을 새로 만들어 기록하지 않았다.

## 협업 피드백
태환: 부가 함수3개 구현 일정·정상 빈 결과 기준, 실제 관련 추천이 가능한 근거 자료를 협의한다.
시영: 실제 fields/활동 근거·직무/관련링크 자료를 보강하되 원문에 없는 내용을 만들지 않는다.
예원: 실제 추천0건 안내와503의 '기능 준비 중' 문구를 기능 미구현/장애로 나눌지 검토한다.
PR #7을 먼저 병합하고 후속 추천 PR을 검토한다. main 직접 push·강제 push·자동 병합은 하지 않는다.

---
## 아래는 이전 시점의 검증 기록

# 공고 조회 API 활성화·화면 연결 검증 — 2026-11-13

## 기준과 범위
- 기준 main:7fc193fbfa4f50274b34f8e6f31bd4e15c60fed9. 브랜치 backend/opportunity-api, 계약4.1-draft.
- 사용자가 전달한 태환 검토:건희 담당으로 DB 목록·상세 및 opportunities 활성화, 초기화용 플래그 검사 개선을 허용.
- 관련 링크 조회를 구현하지 않았으므로 resource-links는 OFF. 추천·직무·활동·면접 HTTP도 OFF다.
- 공통 모델/요청/응답 필드는 변경하지 않았다. 기능 상태·라우팅과 관련 검사의 변경이다.
- 아직 커밋·push·PR 생성·main 병합을 하지 않았다. 아래는 로컬 검증 결과다.

## 실제 구현
- backend/opportunity_query.py:SQLite 읽기 전용 snapshot, schema/mode/모델/ID/출처 관계 재검증, ID정렬·페이지 처리·상세.
- backend/main.py:기존 목록/상세 503 stub 제거 후 라우터를 한 번 등록. capabilities 구현 registry와 설정 일치 검증.
- contracts/FEATURES.json:opportunities만 true/true/이유null. 구현된 기능을 OFF할 때는 true구현 유지+enabledfalse+이유 지정.
- feature gate가 false면 DB를 읽기 전에503. 조회불가503/없는ID404/잘못된페이지422/정상빈DB200빈배열.
- 공고 원본·출처·근거·날짜를 그대로 반환한다. UI는 기존 날짜 표시 코드를 사용한다.
- main연결·설정 검증10건을 추가하고 초기화 단계의 기존 테스트·smoke 기대를 실제 구현 상태로 갱신했다.

## 실제 검사
Python3.12.7·고정requirements의 기존 가상환경 재사용. Node24.18.0/npm11.16.0.
- data_pipeline/tests + backend/tests + tests/integration:227 passed, 기존AnyIO 경고1,21.98s.
- 처음 route중복 테스트에서 새 FastAPI의 included router 구조를 평면으로 가정해 1건 실패했다.
  실제 라우터 트리를 재귀적으로 검사하도록 테스트를 고친 뒤 전체 재검사 통과. HTTP200 검사도 포함한다.
- 전용 query16건, 추가 activation10건 포함. 실제 DB를 이용한 테스트이며 feature OFF 시 DB비접근만 sentinel을 사용했다.
- scripts.validate_examples / scripts.check_generated / pip check:통과.
- npm ci / generate:types / check:generated / typecheck / test24건 / build:모두 통과.
- OpenAPI·모델필드·생성TS 내용은 기존과 같다. 생성TS의 줄바꿈 갱신은 의미상 변경이 없다.
- scripts.smoke_servers:실제 main FastAPI health/options/capabilities와 Vite HTTP 기동 통과.
- git diff --check와 최종 전체 제안 patch 검사:통과.

## 예원 화면 실제 연결 검사
로컬 전용 프로세스2개(FastAPI/Vite)를 별도 포트에서 실행했다. preview=1이나 API응답 대체는 사용하지 않았다.
검증 DB는 work/query-ui-run/real.db이며 시영 normalized자료3건을 importer로 넣었다. 운영DB는 건드리지 않았다.
합성 목표만 입력해 화면에 진입했다. 추천은 OFF여서 외부AI/추천POST는 실행하지 않았다.
1. 공고 탐색에서 실제 목록3건 표시.
2. 상세 펼치기:기관·준비요건·접수마감·게시일·확인시각·원문 링크 표시 확인. 외부원문은 클릭/재검증하지 않았다.
3. 공고ID만 관심공고에 저장하고 새로고침 후 공고를 다시 불러와 실제 상세API200 확인(목록 캐시 없음).
4. 임시DB에서 저장된 공고와 연결행만 제거해 실제404 생성. 화면 '현재 이 공고를 찾을 수 없어요' 확인.
5. 임시DB의 mode를 바꿔 실제503 생성. 화면의503 안내 확인.
6. 임시DB mode복구+importer 재입력 후 다시시도로 상세200 복구 확인.
화면의503 문구는 기존 프론트 공통 안내('기능 준비 중')이며 DB장애 이유 세분화는 이번에 바꾸지 않았다.
임시 오류 실험 후3건을 복구했고 생성한 로컬 서버는 종료했다.

## 실행
README의 Python3.12 설치 후 루트에서 실행한다. 기존DB를 지우지 않는다.
```powershell
$env:DATABASE_URL = "sqlite:///runtime/real.db"
$env:DATA_MODE = "real"
.venv\Scripts\python -m backend.importer --input-dir data/normalized
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
# 다른 터미널에서
npm --prefix frontend run dev
```
실제 조회 검증은 일반 화면 URL을 사용한다. ?preview=1은 예시 응답 모드다.
화면 입력확인→다음→공고탐색→공고불러오기. DB가 없으면 오류이며 자동으로 만들지 않는다.

## 한계와 다음 작업
외부 원문의 최신성, 운영DB, 대용량성능, 외부배포·원격CI는 미검증이다.
검색은 프론트가 불러온 목록에서만 제공한다. 서버검색·추천adapter·관련링크·부가기능은 다음 작업이다.
상세도 현재 전체 catalog를 읽고 검증한다. 데이터 증가 시 DB검증/인덱스/직접조회 최적화를 별도 설계한다.
private importer 스키마 helper를 재사용하므로 향후 DB모듈 분리 때 함께 관리한다.
리뷰·병합 완료를 주장하지 않는다. PR에는 이 기능/공통활성화 범위를 별도로 명시하고 팀원 검토를 받는다.

---

# 공고 목록·상세 조회 검증 — 2026-11-13

기준 main 7fc193fbfa4f50274b34f8e6f31bd4e15c60fed9, 계약 4.1-draft.
브랜치 backend/opportunity-api. 기존 backend-query와 importer 작업은 보존했다.

## 이번 범위와 상태
기존 조회 모듈을 병합된 데이터·추천·프론트 기반으로 옮겨 검증했다.
사용자는 공통 기능 활성화 검토가 아직이며 별도 검토안을 준비하도록 선택했다.
공고 목록·상세 라우터 자체는 구현·검사됐지만 backend/main.py에는 연결하지 않았다.
기본 서버는 기존503/기능OFF 상태다. 실제 화면 연결 완료로 보고하지 않는다.

## 이번 실제 검사
Python3.12.7, 동일 requirements의 ../importer-review/.venv/Scripts/python.exe 재사용.
- pytest backend/tests/test_opportunity_query.py -q --tb=short --basetemp=<새 작업폴더>:16 passed, 경고1,6.30s.
- pytest data_pipeline/tests backend/tests tests/integration -q --tb=short --basetemp=<새 작업폴더>:217 passed, 경고1,23.52s.
- 최초 기본 Temp/pytest-of-antle 접근 권한 실패로 전용16 error, 전체145 pass/72 error가 발생했다.
  작업폴더 안에 UUID로 새 테스트 임시 경로를 지정한 뒤 전부 재실행해 위 결과를 얻었다. 실패를 숨기거나 검사를 skip하지 않았다.
- data_pipeline.normalize --validate-only:출처1/실제 공고3/직무0/링크0 검증 통과.
- scripts.validate_examples, scripts.check_generated, pip check:통과.
- 저장소 외부 work/verify_query_http.py로 별도 uvicorn 테스트 앱을 실행하고 임시 real DB를 실제 HTTP로 읽었다.
  목록200/3건, 상세200 및 원본 일치, 없는ID404, 잘못된페이지422, localhost5173 CORS, DB바이트 불변 확인. 생성한 서버는 종료했다.
- 합성·실제자료는 각각 별도 DB로 검사했다. 실제 데이터란 저장소의 normalized 배치를 사용했다는 뜻이며 외부 원문을 이번에 다시 확인한 것은 아니다.
- 소스·근거·URL·정확한 날짜시각은 공통 모델로 복원해 그대로 반환한다. 접수 상태를 재산정하거나 DB를 수정하지 않는다.

## 공통 검토가 필요한 다음 단계
태환과 docs/changes/opportunity-query-activation.md를 검토하고 별도 공통 PR로 설정·기동검사·통합 기대를 먼저 조율한다.
기존503 라우트를 교체하고 기능 registry/capabilities를 맞춘 뒤 이 라우터를 한 번만 등록해야 한다.
검색파라미터·추천adapter·관련링크조회·기능ON·화면연결은 이번에 구현/반영하지 않았다.
새 OpenAPI·공통 모델·설정·프론트·추천 알고리즘·데이터·기존 integration 테스트는 수정하지 않았다.
기존 private 스키마 검사에 의존하고 매 요청 전체 카탈로그를 검증하므로 대량 성능은 미검증이다.
원격CI·운영DB·브라우저E2E·배포는 미실행. 커밋·push·PR·메시지발송도 하지 않았다.

---

# 공고 조회 내부 구현 인계 — 2026-11-13

기준 main d904e6b / 계약 4.1-draft / backend/opportunity-query.
사용자가 기존 규격의 목록·상세부터 진행하고 공통 변경은 별도 검토하도록 선택했다.

- backend/opportunity_query.py: importer 스키마 v1의 SQLite DB를 읽기 전용·하나의 snapshot으로 읽는다.
- 모델·ID·자료 종류·참조·연결 테이블을 다시 검증한다. ID 오름차순으로 정렬한 뒤 페이지 처리한다.
- 목록·상세 응답은 공통 Page[Opportunity]/Opportunity. 정상 빈 DB는 빈 목록, 없는 ID는404.
- DB 누락·손상·잠금·미지원 버전·demo/real 불일치는503 FEATURE_UNAVAILABLE. DB 자동 생성·쓰기·수집은 없다.
- 제목·출처·근거·날짜는 원본 모델 값으로 반환한다. 조회 시 현재 접수 상태를 재작성하지 않는다.
- 기존 importer의 고정 테이블 상수·스키마 검사·database_path를 재사용한다. 이 private helper 의존은 추후 DB 모듈 분리 때 함께 검토한다.
- 전체 카탈로그를 읽고 검증하므로 대용량 성능은 미검증이다. 검색 인덱스·SQL 페이지 최적화는 별도 작업이다.

## 검사
Python 3.12.7 기존 검토 venv(../importer-review/.venv/Scripts/python.exe)를 재사용했다.
- python -m pytest backend/tests/test_opportunity_query.py -q: 15 passed, 기존 AnyIO 경고1, 2.97s.
- python -m pytest backend/tests tests/integration -q: 140 passed, 기존 AnyIO 경고1, 14.45s.
- python -m scripts.validate_examples: 합성 예시·참조 통과.
- python -m scripts.check_generated: 생성 Python 계약 일치.
- 실제 importer가 만든 임시 DB를 라우터 TestClient에서 읽었다. SQL 응답을 mock으로 대체하지 않았다.
- 테스트에서 조회 전후 DB 바이트가 같음을 확인했다. DB 파일 누락 시 디렉터리도 생성되지 않음을 확인했다.
- 최초 테스트의 파일명 ?는 Windows에서 허용되지 않아 실패했다. 기존 DATABASE_URL 규칙이 금지한 #도 제거하고 한글·공백 경로로 수정했다.
- 원본 패키지나 기존 DB를 수정하지 않았다. 오류 재현은 임시 DB에서만 수행했다.

## 미완료
기본 서버 main의 HTTP 라우트는 기존503을 유지하며 이 라우터는 미연결이다.
기능 활성화·공통 registry/계약 갱신과 기존 integration 기대 변경은 태환 조율 아래 별도 공통 PR에서 진행한다.
검색 파라미터·resource-links 조회·프론트 연결·실제 자료·운영 DB·대용량·브라우저·TCP 서버 E2E·원격 CI·배포는 미구현/미검증이다.
전체 API 활성화 완료나 화면에서 공고 조회 가능 상태라고 보고하지 않는다.
공통 제안: docs/changes/opportunity-query-activation.md.

---

# 현재 백엔드 작업 — SQLite importer

최신 실행 방법·구현 범위·검사 결과는 [importer 인계](handoffs/import-validation/MAIN_VALIDATION.md)를 확인하세요.
기준 main cd8c0ca / 브랜치 backend/sqlite-importer / 계약 4.1-draft.
로컬 전용31개·백엔드/통합125개 통과. 자료 입력은 구현됐고 조회 API·추천 연결은 다음 작업입니다.
사용자가 importer 브랜치 커밋·push를 승인했습니다. PR 생성과 main 병합은 별도 단계입니다.

---

> 아래는 f1997c3 기준 기존 초안의 기록입니다. 현재 보완 상태·검사는 [BOOTSTRAP_HANDOFF.md](BOOTSTRAP_HANDOFF.md)를 우선 확인하세요.

# 백엔드 초기 초안 인계
기준 SHA: 6fcc1821d5ca2c6662313d00ad974e5e86413cac
브랜치: codex/bootstrap / 계약: 4.0-draft (태환 검토 전)
원격 fetch는 현재 Codex 환경의 GitHub 인증 실패로 미완료. 최신 main 기준 여부는 재확인 필요.

## 작성 범위
역할별 폴더·AGENTS, 공동 소유권·Git 절차, 프로필·추천 요청 모델, synthetic 요청 예시,
health·capabilities·미구현 API 오류, 최소 프론트, OpenAPI export, CI 초안.
requirements.txt에 현재 설치된 전이 의존성까지 고정. frontend/package-lock.json 포함.

## 실제 검사
- Python 3.11.9 가상환경 설치 성공.
- python -m pytest backend/tests: 11 passed. 외부 패키지 AnyIO 경고 1건.
- python -m scripts.export_openapi: 성공.
- npm 설치 성공. npm run build: 타입 검사와 Vite 8.3.7 빌드 통과(Node 24.18.0).
- health·capabilities·503·404·개인정보 없는 422 오류는 TestClient로 검증.
- 최초 없는 경로 405 실패를 명시 경로 등록으로 수정하고 11개 재검사 통과.
- 실제 브라우저, 별도 서버 프로세스 HTTP, GitHub CI는 미실행.

## 미완료
전체 공고·출처·근거·추천 응답·부가 모델, 필드 상세표, TS 타입 생성·일치 검사,
전체 공통 자료 참조 검사, 프론트 테스트, SQLite DB·importer·조회·추천 adapter,
실제 공고·외부 AI·통합 시나리오·배포는 미구현 또는 미검증.
현재 기능은 초기 검토용이며 01 전체 초기화 완료가 아니다.
자료 입력 명령은 아직 없다. 설치·실행·종료는 README 참고.
태환과 형식을 검토하고 초기화 보완 후 main에 사람이 병합한 뒤 팀원이 개발을 시작한다.
팀원 네 명의 권한, 브랜치 보호, CODEOWNERS도 미확인/미설정.
