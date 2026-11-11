# 정규화 출력 위치
시영의 후속 작업에서 opportunities.json, sources.json, roles.json, resource_links.json을 생성한다.
각 파일은 shared.models를 따르는 UTF-8 JSON 배열이다. 현재 실제 자료는 없다.
합성 예시는 contracts/examples에만 두며 실제 자료인 것처럼 복사하지 않는다.
shared.validation.validate_dataset으로 ID 참조·혼합 여부를 검증한 뒤 백엔드 importer에 인계한다.
