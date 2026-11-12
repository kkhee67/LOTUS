> 이 문서는 PR #1 병합 전 전달·검토 이력입니다. 최신 실행·검사 결과는 [MAIN_VALIDATION.md](MAIN_VALIDATION.md)를 확인하세요.

# SQLite importer 로컬 인계 검토 — 2026-11-11

## 현재 기준과 보존
원본 저장소: LOTUS, remote=https://github.com/kkhee67/LOTUS.git.
기존 폴더는 codex/bootstrap / HEAD d345f4de8e248fd5375df2411cb8114860f84c86였고 staged·unstaged·untracked가 없었다.
당시 로컬 원격 추적 정보와 비교한 미푸시 커밋도 없었다. 원격 최신 bootstrap과는 다르므로 이 폴더는 갱신·수정하지 않았다.
별도 work/importer-review에 원격 clone 후 backend/importer-review 브랜치를 60f92a2a9c677628319a7af0bb9785369f6a4c2e에서 만들었다.
원격 main은 6fcc1821d5ca2c6662313d00ad974e5e86413cac. GitHub API로 재확인한 PR #1은 OPEN·Draft·미병합, head=60f92a2.
계약 4.1-draft. 검토용 공통 기반이며 main 승인 기준이 아니다.
새 커밋·push·PR 생성·병합·stage는 하지 않았다. 현재 적용 파일은 untracked이며 마지막 기존 HEAD는 그대로다.

## 패키지 검증과 적용
패키지: C:/Users/antle/OneDrive/문서/카카오톡 받은 파일/B1-importer.
APPLY_WITH_CODEX.txt, HANDOFF.md, VERIFY.md, PR_BODY.md, manifest.json, delivery.json,
verify_delivery.py, importer.patch와 실제 importer·테스트를 읽었다.
verify_delivery.py의 inventory/hash 검사와 --phase before 통과.
git apply --check --whitespace=error-all 통과 후 패치 적용, --phase after 통과.
카테고리 A의 7개 파일만 적용했으며 B 공통 문서와 공통 기반 전체는 적용하지 않았다.
원본 패키지와 원본 source는 수정하지 않았다. after 통과는 추가 개선 전 원본 적용 시점의 결과다.
개선 후 importer·테스트의 해시는 의도적으로 전달본과 달라졌고, 별도 개선 diff로 기록한다.

## 환경과 실제 검사
README 기준 Python 3.12.7을 작업 폴더에 준비해 venv+pip로 requirements.txt 고정 버전을 설치했다.
Python 경로 등록/전역 링크는 권한 부족 경고가 있었으나 작업 폴더의 실행 파일로 venv 생성·설치는 성공했다. 프로젝트 의존성은 변경하지 않았다.
아래 python은 work/importer-review/.venv/Scripts/python.exe이다.

| 명령/검사 | 이번 실행 결과 |
|---|---|
| python -m pytest backend/tests/test_importer.py -q (전달 원본) | 20 passed, 10.52s |
| python -m pytest backend/tests tests/integration -q (전달 원본) | 70 passed, 경고 1개, 12.17s |
| python -m pytest backend/tests/test_importer.py -q -k inconsistent (수정 전 회귀 재현) | 4 failed: 모두 손상 DB를 성공으로 처리 |
| python -m pytest backend/tests/test_importer.py -q (보완 후) | 24 passed, 11.94s |
| python -m pytest backend/tests tests/integration -q (보완 후) | 74 passed, 경고 1개, 12.53s |
| python -m scripts.validate_examples | 출처1·공고3·직무1·링크1 및 참조 통과 |
| python -m scripts.check_generated | Python 공통 계약 재생성 일치 |
| python -m pip check | No broken requirements found |
| 원본 importer로 임시 DB 생성 후 개선 importer로 재입력 | 공고 3개 unchanged, 정상 v1 호환 |
| git diff --check | 통과 (tracked 변경 없음) |
| git diff --no-index --check -- /dev/null backend/importer.py 및 테스트 파일 | 공백 오류 출력 없음. no-index의 차이 존재 종료값 1은 예상값으로 확인 |

추가 문서/패치도 최종 공백 검사한다. 경고는 Starlette TestClient의 AnyIO BlockingPortal deprecated 경고이며 숨기지 않았다.
모든 자료는 synthetic 예시와 임시 DB이다. real 모드 테스트도 synthetic 내용을 real 메타데이터로 바꾼 모의 실험이며 실제 자료 확보가 아니다.

## 재현한 문제와 추가 수정
1. DB user_version=1을 유지하고 opportunities_sources 테이블의 PK/FK를 제거하면 원본은 성공했다.
   버전 숫자만 보고 구조를 확인하지 않는 것이 원인이다. 기존 CREATE 문을 helper로 추출하고 메모리 기준 DB의 테이블 DDL과 비교하도록 보완했다.
2. opportunities.source_kind 열만 real로 바꾸고 payload는 synthetic으로 두면 원본은 성공했다.
   payload만 검사하고 별도 열을 읽지 않는 것이 원인이다. 기존 자료의 별도 종류 열도 mode와 대조한다.
3. 출처 연결 행을 삭제하거나 존재하지 않는 항목/출처 연결을 외부 연결에서 삽입해도 원본은 성공했다.
   unchanged 자료는 연결을 건너뛰며 기존 FK 위반은 PRAGMA foreign_keys=ON만으로 검사되지 않는다.
   foreign_key_check 및 payload source_ids와 연결 테이블의 전체 집합 일치 검사를 추가했다.
4개 회귀 테스트에서 CLI 종료 1·IMPORT_FAILED·traceback 비노출·손상 상태를 추가 변경하지 않음을 검증한다.
정상적인 반복 입력·누락 자료 보존·중간 SQL 롤백·잠금 보호 등 원래 테스트는 그대로 유지했다.

## 기존 구현과 내 변경 구분
기존 B1: 네 JSON 배열 공통 모델/참조 검증, sqlite3 저장·관계 테이블, 트랜잭션·upsert·CLI, 테스트 20개, 전달 문서 5개.
이번 Codex 검토: 위 기존 DB 사전 검사 보완, 회귀 테스트 4개, 이 REVIEW 문서·PR 초안·원본 대비 diff.
건희·시영의 사람이 직접 검토했다고 기록하지 않는다. 회의·팀 승인·새 원격 CI를 수행했다고 주장하지 않는다.

## 저장 방식 검토와 한계
모델 검증된 JSON payload 원본과 출처 관계 테이블은 후속 ID 조회 및 모델 복원에 사용할 수 있다.
BEGIN IMMEDIATE부터 모든 쓰기·기존+입력 참조 검증을 하나의 트랜잭션으로 처리하며, SQL 실패 롤백/잠금 거부를 테스트했다.
검색·정렬은 payload 복원 또는 SQLite JSON 조회를 활용할 수 있지만 검색용 열·인덱스는 없고 매 입력마다 기존 전체를 읽으므로 대량 성능은 미검증이다.
DDL 비교는 의도적으로 엄격하다. 의미가 같아도 따옴표·다른 표현으로 수작업 재생성한 테이블은 거부할 수 있다. 이 경우 우회하지 않고 마이그레이션 검토한다.
현재 테이블 정의를 유지하므로 schema_version은 1이며 정상 기존 DB를 바꾸거나 자동 복구하지 않는다.
외부 DB 도구의 임의 편집을 안전하게 복구하는 기능이나 악성 트리거 전반에 대한 보안 감사를 제공하는 것은 아니다.

## 미검증·미완료
실제 자료·운영 DB·대용량 성능·조회 API·추천·프론트·수집기·외부 AI·서비스 E2E·원격 CI·배포는 검사/구현하지 않았다.
생성 검사는 Python 계약에 한정하고 프론트 TS 생성/빌드 검사는 이번 importer 범위에서 실행하지 않았다.
PR #1 사람이 검토·병합한 후 새 main(특히 squash SHA 변경)을 다시 비교하고 적용 검사·관련 테스트를 재실행해야 한다.
현재 검토 브랜치에서 곧바로 main 대상으로 PR을 만들면 미병합 공통 기반도 포함된다. 승인 후 기반 반영을 확인하고 importer 변경만 옮긴다.

## 태환에게 전달할 질문 (발송하지 않음)
- 정상 v1 DB 구조는 그대로 유지하면서 손상 구조/자료/출처 연결을 쓰기 전에 거부하도록 보완했는데 이 정책으로 검토할 수 있을까?
- JSON payload 저장은 먼저 유지하고 검색 열·인덱스/자료량 기준은 조회 API 작업에서 별도 조율할까?
- 시영에게 매 배치에 네 배열과 모든 참조 출처를 함께 제공하고 안정 ID·mode를 지키는 조건을 확인 부탁해.
- PR #1 병합이 완료되면 승인된 main SHA를 기준으로 importer만 별도 PR 준비하겠다.
