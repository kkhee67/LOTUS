# 기본 추천 v1 — 로컬 검토 초안

기본 추천 1차 내부 함수 구현. 공통 기반 PR #1 병합 커밋 cd8c0ca를 기준으로 한다.
브랜치 codex/ai/basic-recommendations-v1. 계약 4.1-draft 모델을 재사용한다.
서버 연결·실제 데이터 검증·담당자 검토는 후속 작업이다.

## 구현 범위
recommender.opportunities.service.recommend(request, opportunities, *, now)의 동기 규칙 추천.
공통 모델과 shared.rules를 재사용한다. 전달받은 모델·고정 시각과 저장소 분야 catalog만 사용한다.
DB·웹·시스템 현재 시각·외부 AI·로그·프로필 저장은 사용하지 않는다. 입력 모델은 변경하지 않는다.
공통 모델·계약·API·기능 플래그·프론트·수집기는 변경하지 않는다.
HTTP 추천은 여전히 503이며 내부 추천 구현과 서버 활성화를 구분한다.

## 관련성 점수
- 관심 분야 일치 40, 희망 직무 일치 40, 목표 일치 20, 관련 전공 일치 15. 각 범주 한 번만 가산.
- 합산 후 100 상한. 최소 15이며 근거가 없거나 관련성이 없는 후보로 채우지 않는다.
- 관심/희망 직무는 catalog 코드·표시명·별칭과 정규화 후 정확히 일치해야 한다.
- 목표는 catalog 표현과 단어 경계가 일치해야 한다. NFKC·대소문자·연속 공백 정규화 사용.
- 공고 fields와 fields 근거의 해당 분야 표현, 또는 activities와 activities 근거의 분야 표현을 함께 확인한다.
- 전공은 related_majors의 정확한 일치와 해당 전공 표현이 있는 related_majors 근거가 필요하다.
- 학교·나이·학적·지역·활동 유무는 관련성 점수에 사용하지 않는다. 실제 필수 자격 규칙에는 사용할 수 있다.
- 점수 내림차순 → eligible 우선 → ID 오름차순. candidate_count는 limit 적용 전 수다.
- 알려지지 않은 관심 표현은 임의 분류하지 않는다. 한국어 조사·동의어·복합 직무·부정문 해석은 지원하지 않는다.
  목표의 '개발자'를 '개발'로 추측하지 않는다. 부정 의도도 파악하지 못하므로 의미 분석 품질은 후속 과제다.
- 점수는 설명 가능한 초기 가중치이며 실제 자료·사용자 평가로 보정된 수치나 합격 확률이 아니다.

## 자격·모집 정책
age/text/education 및 all/any/exception을 true/false/unknown으로 재귀 평가한다.
AND는 명확한 false 우선, OR/예외는 명확한 true 우선이며 정보 부족을 false로 바꾸지 않는다.
최상위 필수 규칙 중 false가 있으면 제외한다. 거주 조건에는 residence_region만 사용한다.
complete여도 requirements 텍스트가 있으면 규칙과의 완전한 대응을 보장할 수 없어 unknown이다.
partial/unknown·미해석 조건·입력 부족도 unknown이다. experience_required가 true/null이면
활동 유무만으로 근무 종류·기간을 증명하지 않고 unknown으로 남긴다. 명시된 경력 불필요(false),
전체 조건 complete, 미해석/자유문 조건 없음, 모든 구조화 규칙 충족인 경우만 eligible이다.
이 보수적 기준은 필수 조건을 텍스트로만 남긴 데이터를 eligible로 잘못 확정하지 않기 위한 것이다.
unknown 후보는 확인 주의와 함께 제공하며 eligible도 최종 지원 자격 보증은 아니다.
일반 공고는 shared.rules에서 open인 항목만 제공한다. upcoming/unknown/closed는 제외한다.
active 자격증은 회차 없음·종료된 회차만 있어도 준비 대상으로 유지하되 접수 중임을 주장하지 않는다.
inactive/unknown 자격증 운영 상태는 제외한다. 날짜 마감 당일 주의는 공통 규칙을 따른다.
중복 ID·real/synthetic 혼합·알 수 없는 분야 코드는 오류다. 원문 수집·source_ids 전체 배치 검증은 호출자 책임이다.

## 호출 예
```python
from datetime import datetime
from shared.models import RecommendationRequest
from scripts.validate_examples import validate_examples
from recommender.opportunities.service import recommend
request = RecommendationRequest(profile={'interests': ['개발']})
result = recommend(request, validate_examples()['opportunities'],
                   now=datetime.fromisoformat('2026-11-11T12:00:00+09:00'))
# 합성 job 1개, 자격 unknown. 실제 모집 결과가 아니다.
```
반환 공고 ID를 원본과 결합하는 adapter·조회 API는 건희의 후속 작업이다.
allow_external_ai 값과 무관하게 engine=rules, explanation_source=template이며 외부 호출하지 않는다.

## 검증과 한계
검사 명령: python -m pytest backend/tests tests/integration -q,
python -m scripts.validate_examples, python -m scripts.check_generated, git diff --check.
추천 테스트는 기존 CI 수집 경로 tests/integration에 두었다. 미구현 함수 검사는 추천만 실제 반환 검사로
대체하고 나머지 세 기능의 미구현 검사와 HTTP 503 검사를 유지했다. 테스트 skip/비활성화는 없다.
실제 실행 결과는 아래 검사 기록을 따른다. 실제 데이터 추천·DB·브라우저·운영 배포·원격 CI는 미검증이다.
외부 AI·직무·활동·면접 추천은 이번 범위 밖이다.

### 2026-11-12 실제 로컬 검사
Python 3.12.7, 기존 고정 의존성 가상환경 사용.
- pytest backend/tests tests/integration -q: 145 passed, 기존 AnyIO 경고 1개.
- validate_examples: 합성 자료 1/3/1/1건과 참조 검증 통과.
- check_generated: 생성 Python 계약 일치.
- git diff --check: 통과.
- 초기 실행에서 테스트 fixture의 경력 근거 누락과 기존 추천 미구현 기대 검사가 실패했다.
  fixture를 유효한 공통 모델로 수정하고, 추천 미구현 기대를 실제 함수/HTTP 경계 검사로 교체 후 위 결과를 얻었다.
테스트에는 관련성·근거·자격 3상태·중첩 OR/예외·정확한 마감·자격증 회차·정렬/limit·입력 보존·네트워크 금지가 포함된다.

### main 병합 후 업로드 검증 — 2026-11-12
기준 cd8c0ca (PR #1 병합), Linux Python 3.12.14 및 고정 requirements.txt 사용.
- pytest backend/tests tests/integration -q: 145 passed, 기존 AnyIO 경고 1개.
- pip check, validate_examples, check_generated, git diff --check 통과.
- Windows 인계 파일의 줄바꿈을 LF로 정리했다.
- 실제 자료·DB adapter·브라우저·운영 배포는 미검증이며 팀원 검토가 필요하다.
