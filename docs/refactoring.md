# 서비스 유지보수 리팩터링 — 2026-11-13

## 작업 기준
사용자가 전체 리팩터링을 요청하여 별도 로컬 브랜치 `refactor/service-maintenance`에서 진행했다.
기존 개발 폴더와 원격 브랜치는 수정하지 않았다. 사용자 요청으로 검토용 업로드를 준비했으며 main 병합은 하지 않는다.

업로드 기준은 main `714e87d`이며 #10~#15 선행 변경이 모두 병합된 상태다.
원래 로컬 작업 공간의 Git index가 이 main의 파일 내용과 동일한 것을 확인한 뒤,
별도 `refactor/service-maintenance-pr` 브랜치에 리팩터링 변경만 적용했다.
원래 로컬 리팩터링 작업과 팀원 브랜치는 보존했다. 이 PR은 main 대상 검토용 초안이다.

검색 작업은 이 PR을 먼저 검토하고, 별도 작업 브랜치에서 아래 분리된 모듈을 사용한다.
- 건희: `catalog_store.read_catalog`로 검증된 snapshot을 읽고 별도 검색 함수에서 필터·total·페이지를 계산한다.
  HTTP 라우트는 `opportunity_query.py`, 오류 응답은 `responses.py`를 사용한다.
- 예원: `usePaginatedList`에 검색 조건 변경 시 reset/취소를 연결한다. 기본 hook은 아직 검색 조건을 자동 감지하지 않는다.
  공고 검색 요청은 `api.ts`와 `Explore.tsx`에 연결하고 입력 폼/추천 hook과 섞지 않는다.
- 검색 파라미터는 이번 PR에서 추가하지 않았다. 검색 기능은 별도 변경으로 검증한다.
- 이 PR 브랜치를 직접 수정하지 않는다. 미병합이면 별도 통합 worktree에서 조합해 검사하고,
  병합되면 최신 main 기준으로 검색 변경만 남도록 정리한다.

## 구조 변경과 담당

| 담당 | 변경 | 유지하는 동작 |
|---|---|---|
| 건희 | `catalog_schema.py`에 스키마·중복 키·경로 검증, `catalog_store.py`에 읽기 전용 snapshot 분리 | 잘못된 DB는 거부, 원본·출처 참조와 mode 검증, 읽기 요청은 DB 변경 없음 |
| 건희 | `responses.py`로 오류 응답 생성 통일 | 기존 HTTP 상태·code·문구·응답 구조와 #10 오류 처리 |
| 예원 | `ProfileForm` 424줄 → 142줄, `ProfileEditor`/`ProfileFields` 분리 | 폼을 숨길 때도 입력과 선택을 유지, 화면 전환·접근성·DOM 구조 유지 |
| 예원 | `useServiceConnection`/`useRecommendationRequest`와 `useApiTask.reset` | 입력 변경·재접속·unmount 때 요청 취소, 오래된 요청 결과 무시 |
| 예원 | `usePaginatedList`/`appendPage`로 공고·사이트 페이지 처리 통일 | 순서 유지, 중복 ID 최신 값으로 교체, 실패 후 기존 목록 유지 |
| 태환 | `policy.py`에 추천 가중치·최소/최대 점수 명명 | 관심40·직무40·목표20·전공15, 최소15·최대100 및 정렬·자격 판정 동일 |
| 태환·건희 | 공통 실제 배치/시계 fixture와 격리 브라우저 실행기 | 서버·브라우저 모두 같은 고정 시각, production은 실제 현재 시각 사용 |

기존 importer와 opportunity_query의 공개 import 경로는 호환 alias로 유지했다.
서비스 코드의 새로운 의존 방향은 router/adapter → catalog_store → catalog_schema이다.
API 경로·공통 모델·기능 플래그·생성 계약·원본 데이터·의존성 파일은 바꾸지 않았다.

## 시간에 독립적인 회귀 검사

`conftest.py`와 `tests/support.py`의 opt-in fixture가 실제 배치 임시 DB와 고정 시각을 제공한다.
기준 시각은 2026-11-13T12:00:00+09:00이며 마감 전·정각·후 검사는 별도 시각을 사용한다.
`tests/browser_server.py`는 테스트 전용 서버다. production 코드에서 import하지 않으며,
운영 API에 시각 변경 endpoint나 요청 필드를 추가하지 않았다.
브라우저 응답의 테스트 시각 헤더도 검사하므로 실제 현재 시각 서버에 실수로 고정 건수를 요구하지 않는다.

```sh
python -m pytest data_pipeline/tests backend/tests tests/integration -q
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run check:generated
npm --prefix frontend run build
python -m scripts.check_generated
python -m scripts.validate_examples
python -m data_pipeline.normalize --validate-only
python -m scripts.smoke_servers
# Playwright와 Chromium이 준비된 환경
python -m scripts.check_browser
# 현재 시각 서버 점검: 실제 공고 수를 고정하지 않고 HTTP/응답 계약을 확인
python -m scripts.smoke_recommendations --url http://127.0.0.1:8000
# 임시 합성 DB의 전체 검증·조회 시간을 측정
python -m scripts.benchmark_catalog
```

브라우저 실행기는 별도 임시 DB·포트·프로세스를 만들고 종료 시 정리한다.
외부 설치된 Playwright/Chromium은 `PLAYWRIGHT_MODULE`/`CHROMIUM_PATH`로 지정한다.
이번 환경에서는 `/opt/codex/cua_node/lib/node_modules/playwright/index.mjs`, `/usr/bin/chromium`을 사용했다.
결과 화면은 Git에서 제외된 `runtime/browser-validation/`에 저장한다.

## 검증 결과
- Python 366개 통과. 프로세스 정리 회귀 5건 포함. 기존 AnyIO deprecation 경고 1건.
- 프론트 27개 통과. 중복 페이지 병합·빈 마지막 페이지 회귀 2건 추가.
- 타입·빌드·생성 계약·실제/합성 데이터·pip check·실제 main/Vite HTTP smoke 및 현재 시각 추천 smoke 통과.
- 고정 시각 PC 1280px·모바일 390px: 실제 추천 2건/40점/unknown, 공고3건, 관심 ID 저장, 입력 변경 후0건 통과.
- 실제 임시 DB 이동으로503 발생 → 복원 → 재시도200. 요청 limit만1로 전달하여 후보2/반환1 안내 확인. 응답 대체 없음.
- 입력값 유지·진행 중인 이전 추천 요청 취소·가로 넘침과 브라우저 예외 없음 확인.
- 기능 상태 조회의 통신 실패를 별도로 주입하고 연결 다시 확인으로 복구하는 검사도 통과했다. 개발 모드의 중복 요청을 고려해 재시도 전까지 실패를 유지한다. 이는 실제 DB 장애 검사와 구분한다.

## 성능 측정과 한계
임시 합성 공고3/300/3000건으로 warm-up 후9회 전체 `read_catalog` 실행의 중앙값을 비교했다.
이 검사는 HTTP·동시사용자·운영 환경 벤치마크가 아니다.

| 공고 수 | 변경 전 | 변경 후 |
|---|---:|---:|
| 3 | 0.833ms | 0.539ms |
| 300 | 16.669ms | 17.732ms |
| 3000 | 343.243ms | 352.343ms |

캐시한 것은 변하지 않는 기준 스키마 정의뿐이다. 매 요청의 실제 DB 스키마·참조·원본 검증은 유지한다.
warm 상태에서도 새 데이터 변경을 읽고 이후 스키마 손상을 거부하는 회귀 검사를 추가했다.
소규모의 반복 준비 비용은 줄었지만 대량 조회 개선은 입증되지 않았다. 단일 측정의 차이를 성능 보장으로 해석하지 않는다.
전체 검증을 생략하거나 DB 내용 캐시를 추가하지 않았다. 대량 성능은 snapshot 갱신·손상 감지·잠금·모드 전환 정책을
정의한 뒤 별도 작업으로 개선해야 한다. 이번 리팩터링으로 대량 성능 문제까지 해결했다고 주장하지 않는다.

## 브라우저 검사 종료 처리 보완
예원 검증에서 Windows의 `servers.log` 잠금으로 기능 검사가 끝난 뒤 임시 폴더 삭제가 실패했다.
실행기가 임시 로그 파일을 서버에 전달하지 않도록 변경하고, `scripts/processes.py`에서
검사 전용 프로세스 트리를 정리한다. Windows는 실행 중인 소유 PID에만 `taskkill /PID … /T /F`를
적용하며, POSIX는 별도 세션의 프로세스 그룹을 종료한다. 서버 생성 도중 실패하거나 브라우저가
실패/시간 초과한 경우에도 ExitStack과 context manager를 통해 정리한다. 정리 실패를 성공으로 숨기지 않는다.

Linux에서 성공·실패 시 자식 서버 포트 종료/로그 삭제, 시간 초과 정리, Windows 명령 호출과
실패 전달을 검사했다. Windows 명령 검사는 모의 실행이며 실제 Windows 재검증은 남아 있다.
PC·모바일 실제 API 브라우저 회귀와 실행기 종료 코드 0도 Linux에서 확인했다.
