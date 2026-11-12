# 공고 조회 활성화 검토 반영

사용자가 전달한 태환 검토에 따라 opportunities만 활성화하는 로컬 구현과 화면 검사를 완료했다.
현재 결과는 docs/backend.md의 최상단 기록을 따른다. 아래 내용은 이전 제안 이력이다.
검색 파라미터 추가는 여전히 미합의·미구현이다. 원격 PR은 아직 생성하지 않았다.

---

# 조회 API 공통 연결·활성화 제안 (미승인)

기준 main 7fc193fbfa4f50274b34f8e6f31bd4e15c60fed9 / 계약 4.1-draft.
사용자 선택: 이번에는 목록·상세를 먼저 구현하고 공통 변경은 별도로 검토한다.
이번 backend/opportunity-api 브랜치는 backend 내부 라우터·테스트와 인계만 준비했다.
backend/main.py, shared/, contracts/, tests/integration/, 프론트·의존성·CI는 수정하지 않았다.

## 별도 공통 PR에서 검토할 내용
- 태환 조율, 건희·예원·시영 영향 검토 후 기능 연결 기준 반영.
- backend/main.py의 기존 목록·상세 503 라우트를 제거하고 create_opportunity_router(settings)를 한 번만 include한다.
  같은 경로를 중복 등록하면 앞의 503 라우트가 계속 실행되므로 단순 include 추가로 해결하지 않는다.
- 현재 초기화 전용 기동 검사(any enabled/implemented이면 오류)를 실제 구현 registry와 설정 일치 검사로 교체한다.
- contracts/FEATURES.json의 opportunities 구현·활성 상태와 unavailable_reason을 실제 연결 상태에 맞춰 변경한다.
- 공통 계약의 조회 현재 상태 표와 OpenAPI를 재생성하고, integration/프론트의 현재 503·전체 미구현 기대를 검토·갱신한다.
- 이 설정·통합 기대 변경은 본 브랜치에서 몰래 반영하지 않고 별도 공통 변경으로 검토한다.
- GET /api/v1/opportunities: limit 기본20(1~100), offset 기본0(0 이상). Page[Opportunity] 유지.
- GET /api/v1/opportunities/{id}: 원본 Opportunity 유지. 없는 ID는404, 정상 빈 DB 목록은200 빈 배열.
- DB 파일 누락/손상/잠금/미지원 스키마/모드 불일치는503 FEATURE_UNAVAILABLE로 처리한다.
  실패를 가짜 빈 성공으로 바꾸지 않는다.
- 현재 구현은 원본 공고·근거·정확한 시각을 보존한다. 날짜 기반 계산 상태를 표시할 필드는 따로 합의한다.

## 검색 규격 제안 (아직 구현하지 않음)
- q라는 선택 문자열을 제안하되 이름·최대 길이·빈값 처리·검색 필드는 태환·예원·시영이 합의한다.
- 후보: 제목·기관·요약의 대소문자 무시 부분일치, 필터 후 total 계산, ID 오름차순 정렬 후 페이지 처리.
- 유형·분야·지역·접수 상태 필터도 별도 규격 합의 전 임의로 추가하지 않는다.

## 인계 상태
라우터 단독 TestClient 검사는 완료했지만 기본 서버 main에는 연결하지 않았다.
활성화 공통 PR을 검토·병합한 후 최신 main을 반영해 실제 서버 연결/E2E를 다시 검사한다.
원격 commit·push·PR 생성·팀원 메시지 발송은 이번에 하지 않았다.
