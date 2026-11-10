# 태환에게 전달할 초안
백엔드 초기 틀을 준비했어. 기술은 프롬프트의 React·TypeScript·Vite / FastAPI·Pydantic / SQLite 기준이야.
전체 통합은 네 담당이고 나는 초기 프로젝트·서버·DB·API를 맡도록 문서를 정정했어.
먼저 AGENTS.md, docs/OWNERSHIP.md, contracts/CONTRACT.md, contracts/INTERNAL_APIS.md를 같이 검토하자.
현재 실행되는 건 health·capabilities, 미구현 503 처리, 최소 프론트 기동 코드야.
프로필·추천 요청 모델만 초안이고 공고·추천 응답·부가 모델과 DB·추천 연결은 아직 없어.
입출력과 추천 함수 서명, 공통 설정 변경 절차를 확인해 줘. 검토된 기준이 main에 들어간 뒤 각자 개발 시작하자.
아직 GitHub PR·CI·팀원 권한은 확인 전이며 완료로 처리하지 않았어.
