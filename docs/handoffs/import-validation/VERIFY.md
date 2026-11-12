> 이 문서는 PR #1 병합 전 전달·검토 이력입니다. 최신 실행·검사 결과는 [MAIN_VALIDATION.md](MAIN_VALIDATION.md)를 확인하세요.

# B1 전달물 검사
이번 인계 준비에서 로컬 검사를 다시 실행했다. 과거 결과를 복사한 것이 아니다.

| 명령 (.venv/Scripts/python 사용) | 이번 로컬 결과 |
|---|---|
| python -m pytest backend/tests/test_importer.py -q | 20 passed (10.05s) |
| python -m pytest backend/tests tests/integration -q | 70 passed, 경고 1개 (12.04s) |
| python -m scripts.validate_examples | 합성 예시·참조 통과 |
| python -m scripts.check_generated | 생성 계약 일치 |
| git diff --check | 통과 |

Starlette/AnyIO DeprecationWarning 1개는 기존 경고이며 숨기지 않았다.
실제 DB 테스트는 임시 경로의 synthetic 자료를 사용한다. SQL 실패 주입은 복구 시험이며 운영 장애 기록이 아니다.

## 적용 재검사
기준 60f92a2의 깨끗한 소스 공간에서 importer.patch만 적용한다. 공통 문서 패치 B는 필요하지 않다.
패키지 루트의 verify_delivery.py로 파일 해시 및 적용 전후 상태를 확인한다.
```powershell
python <package>/verify_delivery.py
python <package>/verify_delivery.py --target <검토폴더> --phase before
# 검토폴더 루트에서 실행
 git apply --check --whitespace=error-all <package>/importer.patch
 git apply --whitespace=error-all <package>/importer.patch
python <package>/verify_delivery.py --target <검토폴더> --phase after
python -m pytest backend/tests/test_importer.py -q
python -m pytest backend/tests tests/integration -q
python -m scripts.validate_examples
python -m scripts.check_generated
```
대상 환경의 Python 가상환경을 사용한다. 패키지 작성 시 적용 재검사 상세 결과는 패키지 루트 receipt.json에 기록한다.
깨끗한 소스 공간의 검사는 설치된 기존 가상환경을 재사용하며 새 의존성 설치 성공을 의미하지 않는다.
PR #1은 OPEN/미병합이므로 검토용 공통 기준 검사다. 승인된 main 기준·전체 서비스 최종 재현과 구분한다.
공통 기반이 수정되거나 squash 등으로 기준이 바뀌면 새 기준에서 적용·검사를 다시 수행한다.

미실행: main 승인 기준 적용, 담당자 직접 검토, 실제 자료 입력·서비스 E2E, 새 원격 CI, 외부 배포.
반복 입력·갱신·빈 입력 보존·참조/모드 오류·SQL 롤백·DB 잠금·미지원 스키마·CLI 비노출은 전용 테스트에 포함된다.
