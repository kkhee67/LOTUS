# 응답 검증 오류 안전 처리 — 2026-11-13

기준0138da6(PR #8), 별도 로컬 브랜치 backend/error-safety, 작업폴더 work/backend-errors.
기존 실제추천 검증 work/backend-ready의 미커밋 작업과 PR #7/#8은 그대로 보존했다.

## 재현한 문제
GET /options의 반환 데이터를 의도적으로 잘못된 형태로 바꿔 ResponseValidationError를 유발했다.
기존 Exception용500 처리기는 Starlette의 바깥 ServerErrorMiddleware에 등록되어 응답 후 예외를 재전파한다.
그 예외의 문자열에는 검증 실패 데이터 원문이 포함되므로 ASGI 서버 로그에 기록될 수 있다.
또한 이 바깥500 경로는 안쪽 CORS 미들웨어를 거치지 않아 허용 origin의 오류 읽기도 실패할 수 있다.
수정 전 전용 재현 테스트1건이 ResponseValidationError 재전파로 실패했다. 실제 비밀정보 대신 공개된 테스트용 sentinel만 사용했다.

## 최소 수정
backend/main.py에서 ResponseValidationError를 import하고 기존 server_error 함수에 해당 예외의 전용 등록을 추가했다.
이 종류의 예외는 안쪽 ExceptionMiddleware에서 처리되어 안전한 공통500 응답으로 끝나고 CORS도 정상 적용된다.
기존 일반 Exception fallback은 유지한다. 새 API/공통 모델/기능 플래그/의존성/프론트/자료/추천 알고리즘은 바꾸지 않았다.

## 무엇을 막고 어떻게 검사했는지
신규 backend/tests/test_error_safety.py의8개 검사:
- 잘못된 실제 응답 모델이 예외로 다시 튀어나오지 않고500 INTERNAL_ERROR이며 health는 계속200.
- 허용 origin에는 CORS 헤더가 붙고 미허용 origin에는 붙지 않음(2건).
- 깨진 JSON/추가 필드/잘못된 입력 타입은422이며 본문 원문이 응답에 없음(3건).
- 추천 함수가 민감정보 형태의 메시지를 포함해 실패해도500 응답/캡처 로그에 원문이 없고 공고3건 조회와 health200 유지. DB 바이트 불변.
- 별도 Uvicorn 프로세스의 실제 HTTP500/CORS/health를 확인하고 stdout/stderr에 잘못된 응답 sentinel이나 Traceback이 없는지 검사.
실제 서버 테스트는 자기 임시 포트의 프로세스를 항상 종료한다. 운영DB/진짜 개인정보는 사용하지 않았다.

실제 검사:Python3.12.7 ../importer-review/.venv/Scripts/python.exe -m pytest data_pipeline/tests backend/tests tests/integration -q
(실행별 새 절대 basetemp/cache 경로 지정). 결과276 passed/기존AnyIO 경고1/26.98s.
이 숫자는 기준268건+이번 오류안전8건이다. 다른 실제추천 브랜치의8건을 이 결과에 합산하지 않았다.
scripts.check_generated 통과, 전체 제안patch/공백 검사 통과. 프론트 변경이 없어 프론트 검사는 이번에 재실행하지 않았다.

## 한계와 반영 상태
임의의 모든 예외·제3자 로그·프록시 접근로그까지 보호했다고 주장하지 않는다. 이번 수정은 응답 모델 검증 실패 경로에 한정한다.
프로필을 URL/DB/로그에 남기지 않는 기존 지침과 --no-access-log 실행 지침은 계속 필요하다.
이 문서는 로컬 구현·검증 시점의 기록이다. 이후 GitHub 반영·CI·검토 상태는 해당 PR에서 확인한다. 병합은 사람이 진행한다.
