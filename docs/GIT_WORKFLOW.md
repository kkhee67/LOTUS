# Git 작업
초기 브랜치 codex/bootstrap. 이후 origin/main을 fetch하고 codex/<role>/<task>를 만든다.
기존 변경·진행 중 브랜치는 보존하고 reset, clean, force push, 임의 stash를 하지 않는다.
main에서 개발·직접 push하지 않는다. 한 브랜치에 한 작업자만 작업한다.
공통 변경은 AI·통합 담당이 영향받는 담당자와 검토하며 별도 PR로 관리한다.
사용자 승인 범위에서만 commit/push/PR 생성한다. 현재 로컬 초안은 미커밋·미푸시다.
PR에 기준 SHA, 계약 버전, 범위, 검사 명령·결과, 미실행과 의존 사항을 적는다.
다른 팀원 검토와 실제 CI 결과를 확인하고 사람이 병합한다. AI가 만든 PR도 동일하다.
초기화가 main에 반영된 SHA를 확인한 뒤 다른 담당자가 같은 기준에서 시작한다.
