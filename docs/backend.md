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
