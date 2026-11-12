> 이 문서는 PR #1 병합 전 전달·검토 이력입니다. 최신 실행·검사 결과는 [MAIN_VALIDATION.md](MAIN_VALIDATION.md)를 확인하세요.

# B1 정규화 자료 입력·중복 방지
목적: 검증된 네 자료 배열을 반복 입력해도 중복 없이 저장하고 실패 시 기존 DB를 보존한다.
범위: backend/importer.py, 내부 테스트, 이 폴더의 기능 인계 문서. 공통 작업 규칙 변경은 별도 검토용으로 분리한다. 조회 API·추천·수집·UI는 포함하지 않는다.
기준: 60f92a2a9c677628319a7af0bb9785369f6a4c2e / 공통 계약 4.1-draft.
선행: 공통 기반 PR #1 (검토·main 반영 전). B1은 로컬 미커밋 변경이며 원격 전달 가능한 새 SHA가 아직 없다.
검토 담당: 건희(DB·입력·복구), 시영(자료 형식·모드·완전한 출처 포함 조건).
실제 피드백: 아직 없음. 검토 대기.

## 구현과 사용
```powershell
.venv\Scripts\python -m backend.importer --input-dir contracts/examples --database runtime/demo.db --mode demo
```
입력 폴더에 sources.json, opportunities.json, roles.json, resource_links.json이 모두 필요하다.
각 파일은 UTF-8 JSON 배열이다. 배치에서 참조하는 출처는 같은 sources.json에 포함해야 한다.
옵션을 생략하면 backend.settings의 DATABASE_URL/DATA_MODE를 쓴다. CLI는 명시 옵션이 우선이다.
결과에는 테이블별 inserted/updated/unchanged 개수만 출력하고 자료 내용은 출력하지 않는다.
실패 시 종료 코드 1과 IMPORT_FAILED를 반환한다. 내부 traceback·실제 입력 원문은 CLI에 표시하지 않는다.

## 저장 설계
Python 표준 sqlite3만 사용하며 새 의존성은 없다. DB user_version=1.
공통 모델로 검증하고 정규화한 JSON payload를 sources/opportunities/roles/resource_links 테이블에 저장한다.
이는 임의 JSON 입력이 아니라 shared 모델로 재검증 가능한 공고 원본 보존 형식이다.
id는 기본키, source_kind는 별도 열, *_sources 연결 테이블은 외래키로 출처를 참조한다.
현재 검색 전용 열/인덱스·ORM·사용자 프로필 테이블은 없다. 읽기 API는 후속 작업이다.

전체 파일·자료 종류·참조를 먼저 검증하여 잘못된 입력은 DB를 열기 전에 거부한다.
BEGIN IMMEDIATE 후 기존 데이터와 입력을 합친 상태도 검증하고 하나의 트랜잭션으로 upsert한다.
동일 payload는 쓰지 않고 unchanged 처리한다. 출처 연결 갱신 시 해당 항목의 연결만 교체한다.
파일에 빠진 항목은 삭제하지 않는다. 빈 네 배열도 기존 자료를 지우지 않는다.
DB mode는 처음 만들 때 고정한다. real/demo 전환·혼합은 거부하며 별도 파일을 사용한다.
입력 객체/파일은 변경하지 않는다. 프로필/추천 요청은 입력 모델에 없으므로 저장하지 않는다.

## 기존 DB·실패·복구
관리되지 않는 기존 스키마와 알 수 없는 user_version은 거부한다. 자동 DROP/초기화/버전 강등은 없다.
최초 v0 빈 DB에서 v1을 트랜잭션으로 만들며, 향후 버전 변경은 별도 마이그레이션·복구 검토가 필요하다.
쓰기 중 실패는 rollback한다. 잠긴 DB는 최대 5초 대기 후 안전한 오류를 반환한다.
유효한 입력 뒤 새 DB 생성 단계의 운영 오류에는 빈 DB 파일이 남을 수 있으나 실패 자료를 성공으로 취급하지 않는다.
기존 자료를 입력 전 상태로 되돌려야 하는 운영 작업은 서버·importer 중지 후 SQLite backup API로 별도 백업을 확보하고,
검증된 백업을 새 파일에서 확인한 뒤 조율한다. 실행 중인 DB의 단순 파일 복사·삭제로 복구하지 않는다.
현재 자동 백업·운영 배포·과거 버전 마이그레이션은 구현하지 않았다.

## 직접 확인할 항목
- 건희: 저장 형식과 source 연결이 후속 조회에 충분한지; 전체 배치 트랜잭션·동시 쓰기 잠금·복구 정책.
- 시영: 매 배치에 참조 출처를 함께 제공하는 조건, stable ID, 실자료와 합성자료 분리.
- 공통: 필드/API 계약은 바꾸지 않았음. 작업 규칙 변경과 선행 PR 의존관계 검토.
- 입력 누락을 삭제로 보지 않는 정책 및 중간 SQL 오류 후 기존 내용 보존을 직접 재현.

이번 전달물의 실제 검사·재실행은 VERIFY.md, PR 초안은 PR_BODY.md,
전달 적용 지시는 APPLY_WITH_CODEX.txt, 파일 목록은 manifest.json을 확인한다.
실제 데이터 확보·조회 API 연결·팀 승인·원격 CI·전체 서비스 최종 재현·배포는 이번 완료 상태가 아니다.
검토용 공통 커밋에서의 패치 적용 검사는 VERIFY.md를 따른다. main 승인 기준에서의 검사는 아직 수행할 수 없다.

## 전달 범위와 순서
A importer 패키지는 importer.patch와 source/ 아래 실제 새 코드·테스트·기능 문서를 포함한다.
공통 기반 전체는 포함하지 않으며 기준 60f92a2가 먼저 필요하다. PR #1은 재확인 시 OPEN/미병합이다.
공통 작업 규칙·역할·상태 문서는 B 별도 패키지이며 A의 실행 의존성이 아니다.
이번에 새 코드나 테스트 변경은 없고, 기존 미커밋 두 파일의 내용과 일치하도록 포장했다.
Git commit/push/PR 생성·병합은 하지 않았다. 건희 검토·시영 확인은 아직 대기다.
