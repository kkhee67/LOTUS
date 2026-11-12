# SQLite importer — 병합된 main 기준 검증

- 기준 main: cd8c0ca5f99002d5a81b33ec60c6b54a93ca614d (PR #1 병합, 날짜 수정 e8821d5 포함).
- 계약: 4.1-draft. 브랜치: backend/sqlite-importer.
- 검토 전 폴더와 미커밋 importer 개선 작업은 그대로 보존했다. 새 clone에서 작업했으며 main 자체는 수정하지 않았다.
- B1 전달 importer를 재사용하고 기존 DB 무결성 개선분을 유지했다. 새로 재개발하지 않았다.

## 기능과 입력
sources.json, opportunities.json, roles.json, resource_links.json 네 UTF-8 JSON 배열을 함께 검사한다.
같은 배치에서 참조하는 출처가 sources.json에 있어야 한다. ID는 안정적으로 유지한다.
검증 후 SQLite에 ID 기준 추가·갱신한다. 동일 자료는 unchanged, 빠진 자료는 삭제하지 않는다.
입력 파일은 변경하지 않는다. 오류 시 전체 롤백하며 CLI에는 원문·traceback을 출력하지 않는다.
DB는 demo/real 모드를 고정하고 다른 모드 자료는 별도 DB에 입력한다.
사용자 프로필·추천 요청은 저장하지 않는다.

## 설치·실행
저장소 루트에서 Python 3.12로 환경을 준비한다. 기존 .env나 DB를 덮어쓰지 않는다.
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m backend.importer --input-dir contracts/examples --database runtime/demo.db --mode demo
```
위 예시는 합성 자료 전용이다. 실제 자료가 아니다.
실제 정규화 자료는 네 파일을 data/normalized에 준비한 뒤 --input-dir data/normalized --database runtime/real.db --mode real로 실행한다.
real 자료의 공개·출처·확인 시각은 데이터 담당자가 별도 검증해야 한다.
--database와 --mode 생략 시 backend.settings의 DATABASE_URL·DATA_MODE를 사용한다. --input-dir은 필수다.
CLI는 정상 종료 0, 입력·DB 실패 1을 반환한다.

## 저장·복구 경계
sqlite3, 스키마 user_version=1. 검증된 JSON payload와 별도 출처 관계 테이블을 저장한다.
기존 DB의 실제 관리 테이블 정의·외래키·자료 종류 열·payload와 출처 연결 일치를 확인한다.
손상/미지원 스키마는 임의 복구하지 않고 거부한다. 정상 원본 v1 DB는 호환된다.
DDL 비교는 공백·대소문자 정규화 기준이며 수작업으로 의미상 동등하게 만든 다른 DDL도 거부할 수 있다.
추가 검색 열·인덱스·향후 스키마 변경은 마이그레이션과 복구 검토가 필요하다.
운영 복구 전에는 서버/importer를 중지하고 SQLite backup API로 백업을 확보한 뒤 새 파일에서 검증한다.
현재 자동 백업·버전 간 마이그레이션은 없다. DB 삭제나 실행 중 파일 단순 복사로 복구하지 않는다.

## 이번 실제 검사 (2026-11-12)
Python 3.12.7, requirements.txt가 동일한 기존 검토용 가상환경을 재사용했다. 새 환경 설치를 수행한 것은 아니다.
아래 python은 검토 시 ../importer-review/.venv/Scripts/python.exe를 사용했다.

| 명령 | 실제 결과 |
|---|---|
| python -m pytest backend/tests/test_importer.py -q | 31 passed, 12.73s |
| python -m pytest backend/tests tests/integration -q | 125 passed, 기존 AnyIO 경고1, 13.88s |
| python -m scripts.validate_examples | 합성 출처1/공고3/직무1/링크1 및 참조 통과 |
| python -m scripts.check_generated | 생성 Python 계약 일치 |
| python -m pip check | 의존성 문제 없음 |
| 실제 CLI로 임시 DB에 같은 합성 배치 두 번 입력 | 첫 실행 6개 추가(출처1/공고3/직무1/링크1), 두 번째 전부 unchanged |

초기 패치 검사에서 Windows CRLF가 공백 오류로 잡혀 저장소 밖 작업용 패치만 LF로 정규화한 후 --whitespace=error-all 검사·적용했다. 원본 패키지는 수정하지 않았다.
추적·미추적 파일과 전체 제안 패치의 공백 검사 및 적용 일치 검사도 마지막에 수행한다.
운영 DB를 대상으로 오류 실험을 하지 않았다.

## 기존 구현과 추가 작업
- B1 전달 구현: 네 배열 검증, 모델/ID/출처 검사, 트랜잭션 upsert, 누락 보존, CLI, 원본 테스트20개.
- 이전 Codex 검토: 기존 DB 스키마·종류·연결 검사와 손상 회귀 테스트4개.
- 이번 작업: 최신 main 위에 기존 구현·개선분 적용. 날짜-only 필드6곳의 잘못된 시각 입력 거부/기존 DB 보존,
  정확한 자정 마감의 DB 왕복 보존·판정·반복 입력 확인 테스트1개 추가(총7개).
- 원래 인계 문서와 manifest는 전달 시점 이력이다. 현재 상태는 이 문서가 우선이다.
- 공통 모델/API·날짜 함수·의존성·CI·프론트·수집기·추천 알고리즘은 이번에 수정하지 않았다.

## 완료·미완료
로컬 importer 재검증 완료. DB 입력만 가능하며 화면 조회·검색·추천 연결은 아직 미구현이다.
capabilities는 기존 미구현 설정을 유지한다. 실제 조회가 구현된 것으로 표시하지 않는다.
실제 자료 입력·운영 DB·대량 성능·서비스 E2E·이번 importer의 원격 CI·배포는 미검증이다.
사람 팀원의 이 importer diff 검토와 승인도 아직 대기다. 다른 팀원에게 검토 요청을 발송하지 않았다.
2026-11-12 사용자가 backend/sqlite-importer 커밋·push를 승인했다. PR 생성·main 병합은 이번 승인에 포함되지 않는다.
