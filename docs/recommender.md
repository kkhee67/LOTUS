# 기본 추천 모듈 준비 상태

## 기준과 확인 결과

- 확인일: 2026-11-11 (Asia/Seoul).
- 저장소: https://github.com/kkhee67/LOTUS
- 작업 브랜치: `codex/ai/basic-recommendations`.
- 기준 `origin/main`: `6fcc1821d5ca2c6662313d00ad974e5e86413cac`.
- 공통 계약 버전: 확인 불가. 기준 커밋에는 계약이 없다.
- 원격 main을 실제 조회하고 fetch했다. 추적 파일은 `README.md` 하나이며 내용은 `# LOTUS`이다.
- 작업 전 로컬은 remote와 HEAD 커밋이 없는 `master`였으며 미커밋 파일은 없었다. 지정된 origin을 연결하고 원격 main에서 작업 브랜치를 생성했다.

다음 자료는 기준 커밋의 전체 파일 목록에서 존재하지 않음을 확인했다. 내용을 읽거나 승인된 것으로 간주하지 않았다.

- 루트 및 recommender 하위 `AGENTS.md`
- `docs/GIT_WORKFLOW.md`, `docs/PROJECT.md`, `docs/OWNERSHIP.md`
- `contracts/CONTRACT.md`, `contracts/INTERNAL_APIS.md`, `contracts/FEATURES.json`
- shared 공통 모델, `shared/catalog.json`, `shared/rules.py`
- `contracts/examples` 예시 자료

## 구현 상태와 호출 계약

기본 추천 함수와 테스트는 **미구현**이다. 공통 초기화가 main에 반영되지 않아 계약 의존 구현을 보류했다. 임시 모델, 대체 dict, 백엔드 프로젝트는 만들지 않았다.

사용자가 요청한 예정 경로는 `recommender/opportunities/service.py`이며 예정 함수는 아래와 같다. 이는 실행 가능한 호출 예가 아니며 승인된 내부 계약이 준비되면 다시 확인한다.

```python
def recommend(
    request: RecommendationRequest,
    opportunities: list[Opportunity],
    *,
    now: datetime,
) -> RecommendationResponse:
    ...
```

공통 모델의 실제 import 경로, 요청 필드, 반환 모델 및 계약 버전은 미정이다. 검증된 공통 예시가 없어 실제 호출 예를 제공하지 않는다. 백엔드에서는 아직 이 경로를 import하거나 호출할 수 없다.

## 공통 기반 준비 후 구현할 범위

백엔드가 전달한 요청·공고·now만 사용하는 동기 규칙 기반 추천을 구현한다. DB, 공고 수집, 서버 실행, 외부 AI 호출을 포함하지 않으며 입력 객체를 변경하지 않는다. 백엔드는 반환된 공고 ID를 원본 공고와 결합한다.

점수는 관련성 0~100 정수로 계획하며 확률로 표현하지 않는다. 계산식·가중치·최소 관련성·분야 매핑은 공통 catalog와 evidence 구조 확인 후 구현과 함께 문서화한다. 현재 정해진 계산식이나 검증된 점수는 없다. 사용자 관심·희망 직무·목표를 우선하고 전공은 보조 단서로 쓰며, 학교와 나이 자체를 점수에 반영하지 않는다.

자격 상태는 승인된 규칙에 따라 eligible/ineligible/unknown을 분리한다. 명확한 필수 조건 불일치는 제외하고 OR·예외·미해석 조건을 보존한다. 일반 공고의 접수 상태, 날짜만 있는 마감, 시간대, 자격증 운영 상태와 회차별 접수 상태는 공통 날짜 규칙에 의존한다. 근거 참조는 해당 공고의 실제 evidence만 사용한다. 이 정책들은 아직 코드로 구현하거나 검증하지 않았다.

정렬과 candidate_count는 계약 확인 후 구현한다. 사용자 요청 기준은 점수 내림차순, 동점에서 eligible 우선, 마지막으로 ID 오름차순이며 candidate_count는 필터·최소 관련성 통과 후 limit 적용 전 수다. 빈 결과를 허용한다.

## 검사 기록

- `git rev-parse --show-toplevel`: 작업 루트 확인.
- `git status --short --branch`, `git remote -v`, `git branch --show-current`: 초기 빈 저장소 상태 확인.
- `git rev-parse --verify HEAD`: 초기 HEAD가 없어 실패. 구현 오류가 아니다.
- `git ls-remote https://github.com/kkhee67/LOTUS.git HEAD refs/heads/main`: 제한 환경의 최초 네트워크 시도는 실패. 승인된 확장 실행에서는 성공했고 위 기준 커밋을 확인했다.
- `git fetch origin main`: 성공.
- `git ls-tree -r --name-only origin/main`: README.md만 존재함을 확인.
- `git show origin/main:README.md`: 성공. 제목만 존재.
- `git show origin/main:AGENTS.md`: 파일 부재로 실패.
- `python --version`: Python 3.12.7.
- `py --version`: No installed Python found! 출력. Python 런처는 사용 가능하다고 간주하지 않는다.
- `node --version`: v24.18.0.

승인된 의존성과 테스트 명령, 기존 테스트가 없다. 단위 테스트·기존 회귀 테스트·백엔드 연결·사이트 통합 검사는 모두 **미실행**이다. 테스트 통과나 통합 성공을 주장하지 않는다.

## 테스트 구현 계획

공통 예시 및 synthetic 데이터와 고정 now를 사용한다. 다음을 검사한다.

- 전공만, 관심만, 희망 직무만, 목표만 입력; 전공과 관심 불일치; 알 수 없는 분야.
- 활동 없음과 미입력; 학교 이름에 따른 점수 불변; 명시된 학교 제한; 거주지와 희망 근무지 구분.
- 자격 3상태; OR·예외·미해석 조건; 경력 필수·불필요·미확인.
- 정확한 마감 직전·정각·경과; 날짜만 있는 마감; 접수 시작 전.
- 운영 중 자격증에 접수 중 회차가 없는 경우 및 종료된 회차가 있는 경우.
- 후보 없음·전부 제외·최소 관련성 미달; 점수 범위·동점·정렬·limit·candidate_count.
- 입력 불변성; 공고 ID 및 evidence 참조 무결성; 동일 입력의 결정성.
- 외부 AI 동의 없이 정상 추천; 외부 유료 API 호출 없음.

## 백엔드 인계와 다음 작업

건희가 준비할 항목과 공동 검토 사항은 [공통 기반 요청](requests/recommender.md)에 기록했다. GitHub 이슈나 팀 메시지는 생성하지 않았다.

공통 계약·모델·예시·테스트 환경이 main에 반영되면 최신 기준을 확인하고 AI 소유 범위에서 구현을 재개한다. 기본 추천 검증 이후 직무 설명, 활동 계획, 면접 준비, 외부 AI 설명 보조를 별도 작업으로 검토한다. 전체 통합은 태환 담당이지만 이번 브랜치에는 포함하지 않는다.

최초 준비 시에는 커밋·push를 수행하지 않았다. 이후 사용자가 작업 결과의 GitHub 업로드를 승인하여 이 문서 두 개를 작업 브랜치에 커밋·push하는 범위로 진행한다. PR 생성과 main 병합은 포함하지 않는다.
