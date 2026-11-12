# 단국대학교 채용공지 정규화

공개 채용공지 상세 페이지를 수동으로 확인하고 사실 요약을
`data/raw/dankook_recruitment.json`에 기록한다. 원문 게시물 번호는 `post_id`에,
확인 시각은 시간대를 포함해 `checked_at`에 기록한다.
`dankook.py`는 수동 기록을 공통 모델로 변환하고 게시물 번호에서 원문 주소와 공고 ID를 만든다.
공고 변경을 확인하면 같은 `post_id`에 새 확인 시각을 기록한다.
게시일은 `YYYY-MM-DD`로 기록한다. 분 단위까지 확인한 마감은 시간대를 포함해
`application.closes_at`에 기록하고, 날짜만 확인한 마감은 `application.closes_on`에 기록한다.
정확한 시각과 자료 확인 시각에는 `+09:00` 같은 UTC 오프셋이 필요하다.

저장소 루트에서 공통 의존성을 설치한 가상환경으로 실행한다.

```powershell
.venv\Scripts\python.exe -m data_pipeline.normalize
.venv\Scripts\python.exe -m data_pipeline.normalize --validate-only
.venv\Scripts\python.exe -m data_pipeline.normalize --as-of '2026-11-12T21:01:00+09:00'
.venv\Scripts\python.exe -m pytest data_pipeline/tests -q
.venv\Scripts\python.exe -m scripts.validate_examples
```

첫 명령은 수동 기록과 기존 배열을 검증하고 ID 기준으로 합친다.
같은 ID는 더 최근에 확인한 기록으로 갱신하고, 이번 입력에서 빠진 기존 항목도 보존한다.
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
