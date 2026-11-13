# 기본 추천 v1 — 로컬 검토 초안

추천 3차 로컬 통합 검증. main 7fc193f 이후 건희의 PR #7·#8 기반 0138da6에 미업로드 2차를 결합했다.
현재 브랜치 ai/recommendations-v3. 2차 원본은 /workspace/LOTUS-ai의 ai/recommendations-v2에 보존한다. 계약 4.1-draft 모델을 재사용한다.
서버 연결·실제 데이터 검증·담당자 검토는 후속 작업이다.

## 구현 범위
recommender.opportunities.service.recommend(request, opportunities, *, now)의 동기 규칙 추천.
공통 모델과 shared.rules를 재사용한다. 전달받은 모델·고정 시각과 저장소 분야 catalog만 사용한다.
DB·웹·시스템 현재 시각·외부 AI·로그·프로필 저장은 사용하지 않는다. 입력 모델은 변경하지 않는다.
공통 모델·계약·API·기능 플래그·프론트·수집기는 변경하지 않는다.
현재 3차 작업 공간은 PR #8의 실제 HTTP 추천 adapter를 사용한다. 아래 1·2차의 503 기록은 당시 기준이다.

## 관련성 점수
- 관심 분야 일치 40, 희망 직무 일치 40, 목표 일치 20, 관련 전공 일치 15. 각 범주 한 번만 가산.
- 합산 후 100 상한. 최소 15이며 근거가 없거나 관련성이 없는 후보로 채우지 않는다.
- 관심/희망 직무는 catalog 표현 또는 추천 내부의 명시적 직무 동의어와 정규화 후 정확히 일치해야 한다.
- 목표는 catalog 표현·직무 동의어와 단어 경계 또는 허용 조사 경계가 일치해야 한다. NFKC·대소문자·연속 공백 정규화 사용.
- 공고 fields와 fields 근거의 해당 분야 표현, 또는 activities와 activities 근거의 분야 표현을 함께 확인한다.
- 전공은 related_majors의 정확한 일치와 해당 전공 표현이 있는 related_majors 근거가 필요하다.
- 학교·나이·학적·지역·활동 유무는 관련성 점수에 사용하지 않는다. 실제 필수 자격 규칙에는 사용할 수 있다.
- 점수 내림차순 → eligible 우선 → ID 오름차순. candidate_count는 limit 적용 전 수다.
- 알려지지 않은 표현은 임의 분류하지 않는다. 추천 내부 동의어와 조사 목록은 text.py를 따른다.
- 목표의 부정·제외 표지가 있는 구절은 가산하지 않는다. 부정 목표가 다른 관심 입력의 점수를 취소하거나 후보를 강제 제외하지는 않으며 확인 주의문을 제공한다.
- 의미 분석 전체를 지원하지 않는다. 이중 부정과 '경험이 없지만 배우고 싶다'도 보수적으로 가산하지 않을 수 있다.
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
실제 실행 결과는 아래 검사 기록을 따른다. 초기 검증 범위와 이후 실제 배치 검증 결과는 아래 날짜별 기록을 따른다.
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

### 2차 로컬 개발 — 2026-11-12
업로드된 1차 e3ebed9를 보존하고 별도 브랜치에서 개발했다. 커밋·push·PR 생성 없음.
- 내부 직무 별칭: 개발자·프로그래머·백엔드·프론트엔드·디자이너·데이터 분석가 등 명시 목록만 지원.
- 조사 경계: 개발을, 개발자로, 소프트웨어를 등의 표현 인식. 재개발·개발도상국은 개발로 매칭하지 않음.
- 목표 및 공고 근거의 부정 구절을 점수 근거로 사용하지 않음. 구절 분리는 문장부호와 명시적 연결어에 한정.
- 근거 매칭은 catalog 표현을 사용하며 사용자용 직무 별칭을 근거에 자동 확장하지 않음.
- 필수 자격의 전공·학교 등 정확 일치 규칙에는 동의어·조사 처리를 적용하지 않음.
- pytest backend/tests tests/integration -q: 175 passed, 기존 AnyIO 경고 1개.
- validate_examples, check_generated, git diff --check 통과.
- data/normalized에는 README만 있어 실제 공고 품질 검증은 미실행. 실제 배치가 준비되면 매칭 누락·과잉을 검토해야 한다.

연결 전 확인용 합성 사례 (software 공고에 유효한 분야 근거가 있고 자격·모집 필터 통과 시):
| 입력 | 기대 결과 |
|---|---|
| 희망 직무: 백엔드 개발자 | 40점 |
| 목표: 개발자로 취업하고 싶어요 | 20점 |
| 목표: 개발은 원하지 않음 | 목표 점수 0, 다른 근거 없으면 추천 없음 |
| 관심: 개발 + 목표: 개발은 원하지 않음 | 관심 40점, 목표 0점, 부정·제외 확인 주의 |
| 목표: 개발 말고 디자이너로 취업 | software 목표 0점, design 근거가 있는 후보에 20점 |

검증된 사례는 tests/integration/test_recommendations.py의 test_v2_*에서 재현한다.

### 병합 main 반영 및 2차 보완 — 2026-11-13
기준 7fc193f. 기존 미커밋 2차를 보존하고 fast-forward로 최신 기반을 반영했다.
공통 모델·분야 catalog·프론트·백엔드 API·데이터 원본은 변경하지 않았다.

- 조사 '의'를 지원해 실제 공고의 '사업의 행정 및 운영 지원'을 놓치던 문제를 보완했다.
  사업자·사업의견 같은 다른 단어는 일치시키지 않으며 활동과 활동 근거를 함께 요구한다.
- 사용자 직접 입력 '웹 개발자', '앱 개발자'는 로컬 추천의 software 별칭 후보로 추가했다.
  배포 전 담당자 검토 대상이며 /options의 공식 별칭을 바꾸거나 전 직무 지원을 주장하지 않는다.
  UX/UI 디자이너·데이터 엔지니어 등 미등록 표현은 여전히 임의 매핑하지 않는다.
- '개발 대신 디자인'의 왼쪽 제외 구절도 목표 가산에서 제외한다.
- 마감이 없는 일반 공고에는 checked_at의 정확한 시각과 원문 재확인 주의를 제공한다.
  임의 유효기간이나 종료일을 만들지 않으며 원문을 실시간 재확인했다고 주장하지 않는다.

실제 배치 검증은 저장소의 단국대 3건을 사용하고 원문을 새로 조회하지 않았다.
고정 시각 2026-11-13T00:00:00+09:00에서 관심 '사업'은 186367·186370 두 건을 각 40점,
자격 unknown으로 추천한다. 종료된 186322는 제외된다. 관심 '개발'은 결과가 없다.
186367의 정확한 마감 2026-11-18T23:59:00+09:00부터 해당 공고는 제외된다.
입력 배치 → 임시 SQLite → 공통 모델 → 추천 → RecommendationApiResponse 검증을 통과했다.
이는 실제 HTTP endpoint/화면 통합 완료를 뜻하지 않는다. API는 기존 503 상태다.

예원 화면의 buildRequest를 직접 실행해 등록 선택지의 관심·희망 직무 입력과 직접 입력을
생성하고 공통 요청 모델 및 추천 함수로 검증했다. 21개 사례 통과.
재현 입력은 로컬 runtime/v2-validation/frontend-requests.json에 있으며 합성 입력만 포함한다.
브라우저 조작·HTTP 성공 경로·서비스 E2E·원격 CI·운영 배포는 이번 작업에서 미실행이다.
커밋·push·PR 생성 없음. 후속 검사 결과는 아래 기록을 따른다.

최종 로컬 검사 (Python 3.12.14):
- python -m pytest data_pipeline/tests backend/tests tests/integration -q: 242 passed, 기존 AnyIO 경고 1개.
- data_pipeline.normalize --validate-only, scripts.validate_examples, scripts.check_generated 통과.
- 프론트 buildRequest → 공통 모델 → 추천: 21개 사례 통과.
- git diff --check 통과.

### 3차: 실제 서버·화면 연결 검증 — 2026-11-13
기반 0138da6e05e4c2fc922504509dd822421e36a37d (건희 PR #8, 선행 PR #7 포함).
두 PR은 작업 시작 시 미병합이었다. 해당 코드를 별도 작업 공간에 받아 2차 변경을 복사했으며,
백엔드·프론트·계약·기능 플래그의 추가 수정 없이 기존 구현을 통합 검증했다.
별도 브랜치 ai/recommendations-v3는 upstream을 지정하지 않았다. commit/push/PR 생성 없음.
PR #7·#8 병합 결과가 달라지면 그 main에 재적용·검사해야 한다.

추가 산출물:
- tests/integration/test_recommendation_http_flow.py: 실제 importer DB와 실제 router/추천 함수를 사용하는 고정 시각 HTTP 회귀 검사 5건.
  긍정적 실제 추천 2건, 원본 상세 응답 일치, 근거 참조, unknown, 무마감 주의, DB 바이트 보존,
  빈 결과, limit/types, 정확한 마감 제외, 422, DB 누락 503 및 복구 후 200을 검사한다.
- tests/integration/recommendation_browser.mjs: API 응답 대체·preview 없이 실제 로컬 서버를 사용하는 브라우저 검사.
  1280px·390px 각각 추천 2건/40점/unknown, 원문 URL, 관심 공고 ID만 저장, 공고 목록3건,
  입력 변경 후 빈 결과·기존 결과 제거, 프로필 URL 미포함, 가로 넘침·JS 오류 없음을 확인한다.

실제 서버 실행 (저장소 루트, 준비된 Python 가상환경 사용):
```sh
python -m backend.importer --input-dir data/normalized --database runtime/v3-validation/real.db --mode real
DATABASE_URL="sqlite:///runtime/v3-validation/real.db" DATA_MODE=real CORS_ORIGINS=http://127.0.0.1:5183 python -m uvicorn backend.main:app --host 127.0.0.1 --port 8183 --no-access-log
# 다른 터미널
VITE_API_BASE_URL=http://127.0.0.1:8183 npm --prefix frontend run dev -- --port 5183 --strictPort
# 서버 실행 후, Playwright와 Chromium이 준비된 환경
LOTUS_TEST_URL=http://127.0.0.1:5183 node tests/integration/recommendation_browser.mjs
```
Playwright가 외부에 설치되어 있으면 PLAYWRIGHT_MODULE에 모듈 경로를, 별도 Chromium은 CHROMIUM_PATH에 경로를 설정한다.
이번 실행은 /workspace/LOTUS-ai/.venv/bin/python, /opt/codex/cua_node/lib/node_modules/playwright/index.mjs,
/usr/bin/chromium을 사용했다. 새 프로젝트 의존성을 추가하지 않았다.
브라우저 검사는 실제 서버 현재 시각과 제출된 배치 상태를 사용한다. 11월18일 마감 이후에는
입력 배치 및 예상 건수를 검토해 갱신해야 한다. 고정 시각 HTTP 회귀 검사는 이에 영향받지 않는다.

최종 검사:
- python -m pytest data_pipeline/tests backend/tests tests/integration -q: 314 passed, 기존 AnyIO 경고1.
- 실제·합성 배치 검사, 생성 Python 계약 검사 통과.
- 프론트 typecheck, test 24개, check:generated, build 통과.
- 실제 HTTP 브라우저: PC·모바일 모두 통과. 결과와 화면은 runtime/v3-validation/에 로컬 보관.
- git diff --check 통과.

실제 배치의 긍정 추천 성공은 확인했지만 원문 최신성, 다양한 분야 추천 품질, 운영 성능·배포는 미검증이다.
브라우저 오류 화면 전체는 이번 자동 브라우저 스크립트 범위 밖이며 422/503/복구는 HTTP 테스트로 검사했다.
2차의 로컬 동의어 후보·부정 표현 제약도 유지되며 팀 검토 대상이다.

### 추천 2·3차 GitHub 검토용 업로드 — 2026-11-13
사용자 요청으로 두 단계의 변경을 `ai/recommendations-v2-v3` 하나에 묶었다.
PR 기준은 미병합 #8의 `backend/service-adapters` / `0138da6`이며, 그 브랜치로 병합하지 않는다.
#8이 최신 main의 #13 수정을 보존하여 병합된 뒤 이 PR 대상을 main으로 바꾸고 CI를 다시 확인한다.
기존 로컬 2차·3차 작업 공간은 보존했다. 위의 미업로드 기록은 각 개발 시점의 이력이다.

이번 업로드 코드 자체의 Python 검사 314개와 실제·합성 데이터 및 생성 계약 검사가 통과했다.
main `e01ce93`에 #8과 이번 변경을 적용한 별도 공간에서도 충돌 없이 Python 317개가 통과했다.
프론트 테스트 24개, typecheck, check:generated, build도 통과했다. 기존 AnyIO 경고는 1건이다.
브라우저 실동작은 위 3차 개발 당시의 검사 기록이며 이번 업로드 준비에서는 재실행하지 않았다.

다른 미병합 PR #9 (`9e05696`)와는 테스트 기대값 조율이 필요하다.
`backend/tests/test_real_recommendation.py`의 33·35·62행은 1차의 후보 1건/186370을 전제로 한다.
2차는 '사업의' 활동·근거를 인식하므로 고정 시각 2026-11-13에는 후보 2건이며,
limit=1이면 items는 1건/186367, candidate_count는 2이다.
#9의 HTTP 검사도 기준 시각을 고정하고, 186367 마감 후에는 후보 1건/186370임을 별도로 확인해야 한다.
앞선 전체 결합 검사에서는 이 기대값 차이로 5개 실패·352개 통과였다.
현재 PR은 타 작업자의 #9 브랜치를 수정하지 않으며, 두 PR을 함께 반영할 때 해당 검사를 조율한다.
직무 별칭 제안 검토와 #9 기대값 조율 전까지 초안으로 유지한다.
