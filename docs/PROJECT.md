# 프로젝트
프로필 입력 → 실제 공고 추천 → 근거·조건 확인 → 원문 이동을 우선한다.
React + TypeScript + Vite / Python + FastAPI + Pydantic / SQLite.
초기 서버는 health·capabilities와 명시적 미구현 오류만 제공한다.
DB·추천·수집·최종 화면은 이번 초안에서 구현하지 않는다.
실제 자료와 synthetic 자료를 혼합하지 않고 기본값은 demo다.
프로필은 요청 메모리에서만 사용한다. DB·URL·로그·localStorage에 저장하지 않는다.
외부 AI는 기본 미동의이며 초안은 외부 호출을 전혀 하지 않는다.
