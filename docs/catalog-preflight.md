# DB 실행 전 점검 명령 — 2026-11-13

## 기준·범위
기준0138da6(PR #8), 별도 로컬 브랜치 backend/catalog-preflight, work/backend-db-check.
기존 실제추천/오류안전/페이지 검증의 미커밋 변경은 각 작업공간에 보존했다.
backend/check_catalog.py와 전용테스트, README 실행 예시와 이 문서만 추가했다.
공통 API/모델/설정/의존성/CI/기능 플래그/서버 기동 방식은 바꾸지 않았다.

## 사용
기존 importer로 자료를 입력한 뒤 같은 DATABASE_URL/DATA_MODE 환경에서 실행한다.
```powershell
.venv\Scripts\python -m backend.check_catalog
if ($LASTEXITCODE -ne 0) { throw "DB 점검 실패" }
```
성공 출력 예시(검증된 실제 자료 기준):
```json
{"counts":{"opportunities":3,"resource_links":0,"roles":0,"sources":1},"data_mode":"real","status":"ok"}
```
종료 코드0=DB 검증 정상,1=조회/자료 검증 불가,2=환경 설정 오류,3=예상하지 못한 점검 오류.
1일 때에는 DB 위치·mode·잠금·스키마/자료 상태를 확인한다.2일 때에는 기존 환경 설정을 확인한다.
실패를 자동 복구하지 않고 DB를 지우거나 만들지 않는다. 성공해도 공고 최신성/추천 존재/서비스 전체 준비 완료라는 뜻은 아니다.

## 코드와 막는 오류
Settings로 기존 설정을 읽고 read_catalog의 읽기전용 snapshot 검사를 그대로 사용한다.
새 DB 검증 로직을 복제하지 않으므로 API와 다른 기준으로 정상 판정하는 위험을 줄인다.
정상일 때에는 모드와 각 배열의 개수만 출력한다. 실패 시에는 고정된 상태/코드만 출력해 설정·경로·자료 원문 노출을 막는다.
정상 빈 DB와 없는 DB를 구분하며, 실제/합성 불일치나 손상 DB를 정상으로 넘기지 않는다.
종료 코드로 실행 스크립트가 실패를 확인할 수 있지만 서버 시작을 강제 차단하는 새 설정은 도입하지 않았다.

## 실제 검증
전용 최종12건:정상demo/real2건, 누락1건, mode/스키마/원문손상/참조손상/잠금5건,
설정오류2건, 정상빈DB1건, 예상외 실패 원문미노출1건.
정상·실패 DB는 임시 파일로 만들고 조회 전후 DB 바이트를 비교했다.11건은 실제 python -m 명령의 종료코드/JSON/stderr를 subprocess로 검사한다.
예상외 실패1건은 내부 함수를 테스트용 예외로 바꾸어 반환 코드3과 안전한 출력을 검사한다.
최초 전용11 passed/14.32s 후 예상외 실패 검사를 추가하고 전체를 실행했다.
전체 data_pipeline/tests backend/tests tests/integration:280 passed/기존AnyIO 경고1/35.56s.
이 수는 기준268+점검12건이며 별도 브랜치 테스트를 합산한 숫자가 아니다.
실제 명령:../importer-review/.venv/Scripts/python.exe -m pytest data_pipeline/tests backend/tests tests/integration -q
(실행별 새 절대 basetemp/cache 경로 지정). Python3.12.7 사용.
scripts.check_generated와 전체 제안patch/공백 검사도 통과했다. 프론트 변경은 없어 이번에 재검사하지 않았다.

## 반영 경계
점검 시점의 DB 상태만 확인하며 이후 자료 갱신·운영배포·성능·전체 로그 점검은 범위 밖이다.
이 문서는 로컬 구현·검증 시점의 기록이다. 이후 GitHub 반영·CI·검토 상태는 해당 PR에서 확인한다. 병합은 사람이 진행한다.
