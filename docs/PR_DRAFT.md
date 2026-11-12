# PR 제목·본문 초안
사용자가 업로드를 승인한 뒤 기존 PR #1 갱신에 사용하는 설명 초안이다.

제목: 초기 공통 기반 보완: 모델·API 계약·날짜 규칙·타입 생성과 팀 인계

## 문제와 변경
기존 초안에는 사용자/추천 요청 모델과 health/capabilities만 있어 각 담당이 연결할 공고·응답 계약이 부족했다.
기존 초기화 브랜치에서 전체 공통 모델, 타입 제한 자격 구조, 날짜 계산, 합성 예시·참조 검사,
options 및 미구현 API 골격, OpenAPI/프론트 타입 생성과 팀원별 첫 작업 문서를 보완했다.
실행 가능한 기능은 기반 API와 최소 상태 화면이며, 미구현 기능은 503/FeatureUnavailableError로 구분한다.

## 기준·범위
기준 f1997c3c45d4259c2d09d30d5e052df0b069f984, 계약 4.0-draft → 4.1-draft (검토 전).
사용자 승인으로 태환이 기존 codex/bootstrap 작업을 이어 맡았다. AI 준비 문서는 별도 브랜치에 보존했다.
Python 3.12 / Node 24를 검증·CI 기준으로 맞췄다. OpenAPI 생성 도구의 peer 범위 때문에 TypeScript는 7.0.2 → 5.9.3으로 조정했다.
빈 목록 요소·중복 ID·시간대 누락 등 검증 강화가 있으므로 프론트·데이터 담당의 검토가 필요하다.

## 검증
- Python 50 passed; 기존 Starlette/AnyIO DeprecationWarning 1개.
- 합성 예시 스키마·ID·근거·출처·분야 코드 및 real/synthetic 분리 검사 통과.
- pip check, OpenAPI/모델 명세 재생성 일치, TS 생성 일치 통과.
- 프론트 테스트 2개, typecheck, build 통과.
- 실제 uvicorn health/options/capabilities와 Vite HTTP 기동 검사 통과.
- Git 제외 설정 및 diff 공백 검사 통과.
- 이번 변경의 GitHub CI, 브라우저 렌더링, 실제 데이터/서비스 통합·배포는 미실행.

## 미구현·검토 요청
DB/importer, 조회 API 본개발, 추천 알고리즘/adapter, 실제 수집기, 완성 UI, 외부 AI는 포함하지 않는다.
건희 및 예원·시영이 모델·필드·설정과 담당별 인계를 검토해야 한다. 작성자 외 검토와 사람의 main 병합 후 역할별 작업을 시작한다.
