# 단국대학교 채용공지 3건 정규화 및 검증

이 문서는 데이터 담당 시영의 [PR #3](https://github.com/kkhee67/LOTUS/pull/3) 인계 기록이다.

## 검토 기준

- 로컬 작업 브랜치는 `codex/data/dankook-recruitment`이다.
- [PR #1](https://github.com/kkhee67/LOTUS/pull/1)이 병합된 `main` 커밋 `cd8c0ca5f99002d5a81b33ec60c6b54a93ca614d`를 기준으로 데이터 배치를 검증했다.
- 공통 모델의 계약 버전은 `4.1-draft`다.

## 출처와 확인 결과

[단국대학교 공식 채용공지](https://cms.dankook.ac.kr/ko/web/kor/apply_noti)의 공개 채용공고 세 건을 정리했다. 단국C-앵커사업단 공고는 `2026-11-12T21:00:39+09:00`에 원문을 다시 확인했다.

| 항목 | 확인 결과와 표현 |
| --- | --- |
| 공고 | [단국C-앵커사업단 프로젝트 계약직 연구원](https://cms.dankook.ac.kr/ko/web/kor/apply_noti?_dku_bbs_web_BbsPortlet_action=view_message&_dku_bbs_web_BbsPortlet_bbsMessageId=186370&p_p_id=dku_bbs_web_BbsPortlet&p_p_lifecycle=0&redirect=%2Fko%2Fweb%2Fkor%2Fhome) |
| ID | 게시판 ID `dankook-recruitment`에 사이트 게시물 번호 `186370`을 결합한 `dankook-recruitment-186370`. 게시 제목·확인 시각 수정으로 ID가 바뀌지 않는다. |
| 기관·업무 | 단국대학교 천안캠퍼스, 충남 앵커사업 운영을 위한 행정 및 사업 지원. `type=job`, `subtype=contract`. |
| 게시일 | 2026년 11월 5일. 정확한 게시 시각은 미기재. |
| 접수 | 공식 본문의 상시모집 안내를 근거로 `application.status=open`. 시작일·마감일 및 정확한 시각은 모두 미기재. 별도 채용 종료 여부는 확인되지 않았다. |
| 필수 자격 | 학사학위 이상 소지 또는 학사학위 취득 예정, 임용 결격사유 없음, 남성 지원자의 병역 이행 또는 면제. 현 계약에서 직접 평가할 수 없는 조건은 OR와 적용 대상을 보존해 `unresolved_conditions`에 두고 `requirements_coverage=partial`로 기록했다. |
| 경력 | 국책사업 행정·지원 또는 산학협력단 과제 관리 경력이 우대다. 필수 경력 요건에 관한 명시가 없어 `experience_required=null`로 뒀다. |
| 분야·근무 방식 | 사업 지원은 활동 설명에 기록했다. 분야 코드는 분류 기준을 확인할 때까지 `fields=[]`로 두고, 천안 근무지는 지역으로 기록했다. 근무 방식은 모델 기본값 `unknown`이다. |

### 추가 공고

울트라앵커사업단 프로젝트 계약직은 천안캠퍼스의 인재육성 사업 행정 지원 공고다. ID는 `dankook-recruitment-186367`이며, 게시일은 2026년 11월 5일이다. `2026-11-12T20:48:39+09:00`에 상세 본문을 열람했다. [단국대 공식 원문](https://cms.dankook.ac.kr/ko/web/kor/apply_noti?_dku_bbs_web_BbsPortlet_action=view_message&_dku_bbs_web_BbsPortlet_bbsMessageId=186367&p_p_id=dku_bbs_web_BbsPortlet&p_p_lifecycle=0&redirect=%2Fko%2Fweb%2Fkor%2Fhome)

- 이메일 접수 안내에 따라 `open`으로 기록했다. 정확한 마감은 `2026-11-18T23:59:00+09:00`이고, 접수 시작일과 게시 시각은 미기재다.
- 학사학위 이상, 임용 결격사유, 남성 지원자 병역 이행 또는 면제 조건을 원문 근거와 함께 보존했다. 국책사업 행정·지원 경력은 우대 항목이므로 필수 경력 여부는 `null`이다.

의과대학 학사조교 공고는 접수가 끝난 사례로 포함했다. ID는 `dankook-recruitment-186322`이고, 학사 행정 지원 업무와 학사학위·임용 조건을 기록했다. 게시일은 2026년 10월 20일, 마감은 `2026-11-11T11:00:00+09:00`이다. 접수 시작일과 필수 경력 요건은 원문에 명시되어 있지 않다. `2026-11-12T21:00:39+09:00`에 확인했으며, `closed`로 저장했다. [단국대 공식 원문](https://cms.dankook.ac.kr/ko/web/kor/apply_noti?_dku_bbs_web_BbsPortlet_action=view_message&_dku_bbs_web_BbsPortlet_bbsMessageId=186322&p_p_id=dku_bbs_web_BbsPortlet&p_p_lifecycle=0&redirect=%2Fko%2Fweb%2Fkor%2Fhome) · [천안캠퍼스 위치 근거](https://cms.dankook.ac.kr/ko/web/kor/-512)

## 변경과 검증

- `data/raw/dankook_recruitment.json`은 수동 확인 기록이다. `data_pipeline/dankook.py`에서 게시판 전용 변환을 하고, `data_pipeline/normalize.py`에서 네 배열의 스키마 및 참조를 검증한다.
- 동일 ID는 더 최근 확인 건으로 갱신한다. 기존 자료·확인 시각을 보존하고 입력 누락·중복·스키마 오류가 있으면 배열 교체 전에 중단한다.
- 저장 중 교체 오류가 나면 이미 교체한 배열을 복구한다. 같은 입력을 다시 실행하면 기존 JSON의 내용과 파일 수정 시각이 유지된다.
- Python 3.13.12와 저장소의 고정 의존성으로 실행했다. 공통 기반 CI의 Python 기준은 3.12다.
- `python -m data_pipeline.normalize` 및 `python -m data_pipeline.normalize --validate-only`는 실제 배치 출처 1건, 공고 3건, 직무·링크 각 0건을 검증한다.
- 병합된 공통 모델로 빈 출력 폴더에서 다시 생성한 네 JSON이 기존 출력과 바이트 단위로 일치했다.
- `python -m data_pipeline.normalize --as-of '2026-11-12T21:01:00+09:00'`으로 세 공고의 접수 상태와 마감, 원문 확인 시각을 읽기 전용으로 검사한다.
- `python -m pytest data_pipeline/tests backend/tests tests/integration -q`는 데이터 테스트 19건을 포함해 113건 통과했다. 기존 Starlette의 AnyIO 별칭 사용 중단 경고가 1건 있었다.
- `python -m scripts.validate_examples`로 합성 계약 예시와 참조를 검증했다.
- 자동 갱신, DB importer 및 실제 추천 연동은 이번 작업 범위 밖이다.

## 건희 인계

아래 네 배열을 함께 읽어 참조를 검사한 후 importer에 연결한다. 배치에 직무와 관련 링크 자료는 각각 0건이다.

- [sources.json](../data/normalized/sources.json)
- [opportunities.json](../data/normalized/opportunities.json)
- [roles.json](../data/normalized/roles.json)
- [resource_links.json](../data/normalized/resource_links.json)

## 태환 확인 요청

1. 분야 코드가 비어 있는 사업지원 공고에 대해 활동 설명으로 관련성을 평가할지, `business` 코드의 적용 범위를 문서화할지 확인 부탁한다.
2. 마감일이 없는 상시모집 공고는 확인 시각이 오래됐을 때 어떤 기준으로 재확인 안내를 표시할지 정하면 좋겠다.
3. 학위·임용·병역 조건을 평가할 수 없는 동안 자격은 `unknown`으로 처리하고, 확인이 필요한 조건을 원문 근거와 함께 보여주는지 확인 부탁한다.
