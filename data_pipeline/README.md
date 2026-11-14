# 단국대학교 채용공지 정규화

공개 채용공지 상세 페이지를 수동으로 확인하고 사실 요약을
`data/raw/dankook_recruitment.json`에 기록한다. 원문 게시물 번호는 `post_id`에,
확인 시각은 시간대를 포함해 `checked_at`에 기록한다.
`dankook.py`는 수동 기록을 공통 모델로 변환하고 게시물 번호에서 원문 주소와 공고 ID를 만든다.
공고 변경을 확인하면 같은 `post_id`에 새 확인 시각을 기록한다.
게시일만 확인했으면 `published_on`에 `YYYY-MM-DD`를 쓰고, 게시 시각까지 확인했으면
`published_at`에 시간대를 포함한 시각을 쓴다. 둘 중 하나만 쓰고, 게시일을 모르면 둘 다 생략한다.
분 단위까지 확인한 마감은 시간대를 포함해
`application.closes_at`에 기록하고, 날짜만 확인한 마감은 `application.closes_on`에 기록한다.
정확한 시각과 자료 확인 시각에는 `+09:00` 같은 UTC 오프셋이 필요하다.

지원 조건을 확인하지 못했다면 `requirements`를 생략하거나 빈 배열로 둔다. 원문에 자격 제한이
없다고 명시한 경우에만 `no_requirements_note`에 해당 문구의 요약을 적는다.
필수 경력은 `experience_required: true`, 경력이 필요 없다고 명시했으면 `false`로 기록하고
두 경우 모두 `experience_note`에 근거를 적는다. 경력 우대만 있으면 메모만 적고
`experience_required`는 생략한다. 필수 경력의 근거는 상세 화면에서 볼 수 있도록 지원 조건에도
포함한다. 자동 판정할 수 없는 조건은 원문 요약으로 보존한다.

저장소 루트에서 공통 의존성을 설치한 가상환경으로 실행한다.

```powershell
.venv\Scripts\python.exe -m data_pipeline.normalize
.venv\Scripts\python.exe -m data_pipeline.normalize --validate-only
.venv\Scripts\python.exe -m data_pipeline.normalize --as-of '2026-11-12T21:01:00+09:00'
.venv\Scripts\python.exe -m pytest data_pipeline/tests -q
.venv\Scripts\python.exe -m scripts.validate_examples
```

첫 명령은 수동 기록과 기존 배열을 검증하고 ID 기준으로 합친다.
같은 ID는 더 최근에 확인한 기록으로 갱신하고, 확인 시각이 같으면 오타 등 정정을 반영한다.
오래된 기록으로 덮어쓰지 않고 이번 입력에서 빠진 기존 항목도 보존한다.
입력 파일이 없거나 비어 있거나 검증에 실패하면 출력 교체 전에 중단한다.
내용이 같은 배열 파일은 그대로 둔다. 저장 중 파일 교체에 실패하면 이미 교체한 배열을 이전 내용으로 복구한다.
복구도 실패하면 오류 메시지에 복구 파일을 보관한 경로를 출력한다.
검증 전용 명령은 네 배열을 읽어 스키마와 ID, 출처 참조, 분야 코드, 자료 종류를 검사한다.
`--as-of`는 저장된 공고를 읽어 지정 시각 기준의 접수 상태와 원문 확인 시각을 출력한다.
마감이 기재되지 않은 공고의 마감 표시는 `unlisted`다.
출력 교체는 파일별로 수행하므로 같은 출력 경로에 작업자 한 명이 실행한다.

인계 전에는 기존 배치와 별도로 빈 폴더에서 생성과 검증을 실행할 수 있다.

```powershell
$lotusCheck = Join-Path runtime ('verify-data-' + [guid]::NewGuid().ToString('N'))
.venv\Scripts\python.exe -m data_pipeline.normalize --output $lotusCheck
.venv\Scripts\python.exe -m data_pipeline.normalize --output $lotusCheck --validate-only
```

원문 열람과 기록은 수동이다. 실제 배치는 `data/normalized/`에 저장한다.
합성 계약 예시는 `contracts/examples/`에서 별도로 검사한다.
정규화 JSON은 Windows에서도 LF 줄바꿈을 유지해 새로 체크아웃한 파일과 재생성한 파일을 그대로 비교할 수 있다.
검토 기준, 원문 링크, 건희·태환 인계 사항은 [데이터 인계](HANDOFF.md)를 참고한다.

## 공개 공고 확장 배치

기본 배치는 단국대 공고 3건을 유지한다. 확장 배치는 잡알리오 채용과 주최·게시기관에서 확인한 인턴, 공모전·대회, 교외활동, 교육, 행사, 자격증, 취업지원 안내를 포함한다. 기관별 수동 기록은 `data/raw/organizer_notices.json`에 있다.
같은 기회는 한 번만 등록하고, 학교가 기업 인턴 공고를 게시한 경우 기관은 기업명, 출처는 학교명으로 기록한다.
접수 기간과 행사·활동 일정은 따로 입력한다. 자격증의 운영 상태는 `certification.status`에, 회차별 접수 정보는 `certification.exam_sessions`에 기록한다.
아래 명령은 저장한 로컬 입력만 읽고 `data/normalized/expanded/`에 네 배열을 생성하거나 검증한다.

```powershell
.venv\Scripts\python.exe -m data_pipeline.normalize --include-public
.venv\Scripts\python.exe -m data_pipeline.normalize --include-public --validate-only
```

백엔드 importer에는 `--input-dir data/normalized/expanded --mode real`을 지정한다.
수집 근거와 필드 범위는 [확장 배치 안내](../data/normalized/expanded/README.md)를 참고한다.

## 접수 중심 배치와 화면 분류

`--current-as-of`는 지정한 시각에 접수 중·예정인 공고, 운영 중인 자격 종목, 접수 상태가 미확인인 정책 안내와 종료일이 지나지 않은 미확인 행사를 `data/normalized/current/`에 저장한다. 전체 이력은 확장 배치에 보존한다.

```powershell
.venv\Scripts\python.exe -m data_pipeline.normalize --current-as-of '2026-11-14T12:00:00+09:00'
.venv\Scripts\python.exe -m data_pipeline.normalize --output data/normalized/current --validate-only
```

공고 검색에서 사용하는 텍스트는 제목·기관·요약·태그다. 요약에는 원문에 확인되는 활동·직무를 담고, 태그는 원문으로 확인한 관련어를 입력한다. `related_majors`는 활동·직무와 관련된 전공을 뜻하며, 실제 지원 조건은 `requirements`에 기록한다.
학교가 올린 채용은 `job`, 채용 인턴은 `job`의 `internship`으로 입력한다. 서포터즈·봉사·연구 활동은 성격에 맞는 `project` 등으로 분류한다. 어학 요건은 해당 직무, 인정 시험, 예외가 확인된 경우만 조건에 기록한다. 어학시험 자체는 자격증·검정에 해당한다.
