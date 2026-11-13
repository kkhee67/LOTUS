# 공고 검색 API — 예원 연결 인계 / 로컬 구현

## 기준·의존 관계
main714e87d, PR #16 HEAD bb02a916ca0399849995fdb46e6a6b2b5f546693을 확인했다.
#16은 미병합 Draft다. backend/search-refactored라는 별도 로컬 브랜치에서 #16 구조 위에 검색 변경만 추가했다.
#16 원격 브랜치와 기존 work/backend-search(714e87d,clean)는 수정하지 않았다.
이 문서의 검색 규격은 이번 사용자 요청에 따른 기준이다. 이전 검토안의 q100자/유형8개 제한은 적용하지 않는다.
#16 병합 후 최신main에서 검색patch만 check/재적용하고 diff·CI·팀 검토 후 반영한다. 현재 main에 자동 반영된 기능은 아니다.

## 요청
GET /api/v1/opportunities
| 파라미터 | 규칙 |
|---|---|
| q | 선택 문자열, 전달된 원문 최대200 Unicode code point. 초과422. 생략/빈문자열/200자이내공백만이면 검색조건 없음. 문자열 null은 일반 검색어. |
| types | 선택 반복쿼리. types=job&types=event. 생략은전체,OR. 중복허용하되 결과중복없음. 빈값/미지값/CSV job,event/공백붙인값은422. |
| limit | 기존기본20,1~100 |
| offset | 기존기본0,0이상 |
허용유형:contest,competition,job,certification,event,training,project,notice. 기존 OpportunityType 그대로다.
유형 반복개수에 새 제한을 추가하지 않았다. 공통 모델/응답필드/API버전/기능플래그는 유지한다.

## 검색 정규화와 의미
검색 대상은 title/organization/summary/tags뿐이다. activities/requirements/근거/사용자프로필을 추가 대상으로 삼지 않는다.
비교용 복사본에 Python unicodedata.normalize('NFKC',text).casefold()를 적용한다.
검색어는 정규화 후 split()으로 앞뒤/연속 Unicode 공백을 제거하고 단어로 나눈다.
각 단어가 대상 필드 중 하나에 부분일치해야 한다(단어끼리AND). 여러 단어는 서로 다른 필드에서 일치해도 된다.
유형끼리는OR,유형과검색어는AND다. 필드경계를 이어붙여 하나의 단어를 만들지 않는다.
전각ＡＩ=AI=ai,분해/결합한글동일,CAFÉ=분해accent형태,strasse=Straße 비교가 가능하다.
Python casefold는 JavaScript toLowerCase/toLocaleLowerCase와 완전히 같지 않다. 원본표시/날짜/URL/태그값은 수정하지 않는다.
%와_와따옴표·+는 일반문자다. 정규식/SQL LIKE 패턴을 받지 않는다.
검색조건을 SQL에 넣지 않고 검증된snapshot을 Python의 in 비교로 필터하므로 SQL바인딩/LIKE와일드카드이스케이프를 혼동할 경로가 없다.

## snapshot·페이지·오류
catalog_store.read_catalog를 요청당1회 호출해 DB 스키마·모드·전체payload·중복키·출처·참조를 검증한다.
검증된 전체기회 필터→ID오름차순→total계산→offset/limit 적용. total/items는 같은 반환 snapshot에서 계산한다.
검색무관한 공고의 손상도503으로 거부한다. q가빈조건이어도검증을 건너뛰지 않는다.
마감공고를 자동으로 제외하지 않는다. 추천정책과검색은 별개이며 검색에 추천점수는 포함되지 않는다.
상세 GET /opportunities/{id}는 검색조건과 무관하게 ID 원본을조회한다.
정상0건은200/items[]/total0. 끝초과offset은200/items[]/total은필터전체수유지.
잘못된조건422 VALIDATION_ERROR, DB누락·손상·잠금·real/demo불일치503 FEATURE_UNAVAILABLE.
입력/DB경로/자료원문은오류에노출하지않는다. 공통 responses.error_response와기존422처리기를그대로쓴다.

## 인코딩 예시(프론트 구현에 옮길 코드)
```typescript
import type {paths} from './generated/api';
type SearchQuery = NonNullable<paths['/api/v1/opportunities']['get']['parameters']['query']>;
const query: SearchQuery = {q: input, types: selectedTypes, limit: 20, offset};
const params = new URLSearchParams({limit: String(query.limit ?? 20), offset: String(query.offset ?? 0)});
if (query.q != null) params.set('q', query.q); // 원문 전달: 200자 검사는 서버에서도 수행
for (const type of new Set(query.types ?? [])) params.append('types', type);
const response = await fetch(`${API_BASE}/api/v1/opportunities?${params.toString()}`, {signal});
```
API_BASE는서버origin만이며 /api/v1을중복해서붙이지않는다. 관련사이트/추천요청에검색옵션을섞지않는다.
URLSearchParams가한글/공백/+/%/& 등을한번인코딩한다. encodeURIComponent로미리인코딩하면이중인코딩될수있으니하지않는다.
프로필이나연락처를q에넣지않는다. 검색어는URL에전송된다. 로컬서버는 --no-access-log로실행했다.

## 페이지 상태 연결(예원 담당)
- #16의 usePaginatedList는 검색 조건 변경을 자동 감지하지 않는다. query/types/화면이 바뀌면 reset()으로 이전요청취소·누적items제거·offset0으로시작하도록 연결한다.
- reset()과같은이벤트에서즉시과거closure의load()를호출해이전offset으로요청하지않도록 새조건반영후첫페이지요청을실행한다.
- 같은조건의더보기만appendPage로합친다. total은검색결과전체수이며현재반환items수와다르다.
- 기존 Explore의 로컬 toLocaleLowerCase 필터로 서버결과를 다시 거르지 않는다. NFKC/casefold 차이로 정상일치를누락할수있다.
- 전체검색0건문구를사용하며'불러온목록안에서없음'이라는기존문구는조정한다.
- 선택탭 notices/events는해당types로요청하고조건변경때reset한다. 관심ID상세조회에는검색조건을붙이지않는다.
- 기존 api.ts getList는limit/offset만전송한다. 공고전용검색전달을추가해야 실제화면이이API를사용한다. 관련사이트 getList는변경할필요없다.
이번백엔드작업에서는해당프론트기능소스를수정하지않았고생성타입만갱신했다.

## 검증 서버 정보
현재API:http://127.0.0.1:8021
Swagger:http://127.0.0.1:8021/docs
작업코드:work/backend-search-refactor
임시DB:C:\Users\antle\Documents\Codex\2026-11-10\api-db-api-ai-ai-01\work\search-validation-2232fd31\real.db
실제자료3건을입력한별도검증DB이며운영DB가아니다. 현재로그는 C:\Users\antle\Documents\Codex\2026-11-10\api-db-api-ai-ai-01\work\search-validation-2232fd31\backend.log.
CORS허용origin:http://localhost:5173,http://127.0.0.1:5173.
이주소는이컴퓨터전용이다. 다른팀원PC에공유되는공개배포주소가아니다. 예원PC에서는전달된코드를아래방법으로실행하거나별도공용검증환경을준비해야한다.

```powershell
# 프로젝트 README대로 Python 가상환경 설치 후 저장소 루트에서
$env:DATABASE_URL = "sqlite:///runtime/search-real.db"
$env:DATA_MODE = "real"
$env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
.venv\Scripts\python -m backend.importer --input-dir data/normalized
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8021 --no-access-log
# 프론트 .env.local에서 VITE_API_BASE_URL=http://127.0.0.1:8021 로설정후Vite재시작
```
기존.env/DB를덮어쓰지않는다. 현재코드는로컬미커밋이라GitHub main을받는것만으로검색이생기지않는다.

## 실제 응답 예시
사업검색/job/limit1/offset0:HTTP200,total2,반환1. ID는186367이며다음offset1은186370이다.
```json
{
  "items": [
    {
      "id": "dankook-recruitment-186367",
      "type": "job",
      "subtype": "contract",
      "title": "울트라앵커사업단(초광역 성장엔진 인재육성사업) 프로젝트 계약직 채용 공고(~11.18까지 접수)",
      "organization": "단국대학교",
      "summary": "단국대학교 천안캠퍼스에서 초광역 성장엔진 인재육성 사업을 지원할 프로젝트 계약직을 모집한다.",
      "fields": [],
      "related_majors": [],
      "tags": [],
      "regions": [
        "충남 천안"
      ],
      "work_mode": "unknown",
      "activities": [
        "초광역 성장엔진 인재육성 사업의 행정 및 운영 지원"
      ],
      "requirements": [
        "학사학위 이상 소지",
        "교육공무원 임용 결격사유에 해당하지 않아야 함",
        "남성 지원자는 병역 이행 또는 면제 요건을 충족해야 함"
      ],
      "eligibility_rules": [],
      "requirements_coverage": "partial",
      "unresolved_conditions": [
        "학사학위 이상 소지",
        "교육공무원 임용 결격사유에 해당하지 않아야 함",
        "남성 지원자는 병역 이행 또는 면제 요건을 충족해야 함"
      ],
      "experience_required": null,
      "application": {
        "status": "open",
        "opens_on": null,
        "closes_on": null,
        "opens_at": null,
        "closes_at": "2026-11-18T23:59:00+09:00"
      },
      "certification": null,
      "event_schedule": null,
      "source_ids": [
        "dankook-recruitment"
      ],
      "source_url": "https://cms.dankook.ac.kr/ko/web/kor/apply_noti?_dku_bbs_web_BbsPortlet_action=view_message&_dku_bbs_web_BbsPortlet_bbsMessageId=186367&p_p_id=dku_bbs_web_BbsPortlet&p_p_lifecycle=0&redirect=%2Fko%2Fweb%2Fkor%2Fhome",
      "source_kind": "real",
      "published_on": "2026-11-05",
      "published_at": null,
      "checked_at": "2026-11-12T20:48:39+09:00",
      "evidence": [
        {
          "id": "duties",
          "field": "activities",
          "fact": "초광역 성장엔진 인재육성 사업의 행정 및 운영 지원",
          "source_url": "https://cms.dankook.ac.kr/ko/web/kor/apply_noti?_dku_bbs_web_BbsPortlet_action=view_message&_dku_bbs_web_BbsPortlet_bbsMessageId=186367&p_p_id=dku_bbs_web_BbsPortlet&p_p_lifecycle=0&redirect=%2Fko%2Fweb%2Fkor%2Fhome"
        },
        {
          "id": "conditions",
          "field": "requirements",
          "fact": "학사학위 이상 소지 / 교육공무원 임용 결격사유에 해당하지 않아야 함 / 남성 지원자는 병역 이행 또는 면제 요건을 충족해야 함",
          "source_url": "https://cms.dankook.ac.kr/ko/web/kor/apply_noti?_dku_bbs_web_BbsPortlet_action=view_message&_dku_bbs_web_BbsPortlet_bbsMessageId=186367&p_p_id=dku_bbs_web_BbsPortlet&p_p_lifecycle=0&redirect=%2Fko%2Fweb%2Fkor%2Fhome"
        },
        {
          "id": "application",
          "field": "application",
          "fact": "이메일 접수 마감은 2026년 11월 18일 23시 59분이다. 접수 시작일은 원문에 기재되어 있지 않다.",
          "source_url": "https://cms.dankook.ac.kr/ko/web/kor/apply_noti?_dku_bbs_web_BbsPortlet_action=view_message&_dku_bbs_web_BbsPortlet_bbsMessageId=186367&p_p_id=dku_bbs_web_BbsPortlet&p_p_lifecycle=0&redirect=%2Fko%2Fweb%2Fkor%2Fhome"
        },
        {
          "id": "experience",
          "field": "experience_required",
          "fact": "국책사업의 행정 또는 지원 업무 경력은 우대 조건이다.",
          "source_url": "https://cms.dankook.ac.kr/ko/web/kor/apply_noti?_dku_bbs_web_BbsPortlet_action=view_message&_dku_bbs_web_BbsPortlet_bbsMessageId=186367&p_p_id=dku_bbs_web_BbsPortlet&p_p_lifecycle=0&redirect=%2Fko%2Fweb%2Fkor%2Fhome"
        }
      ]
    }
  ],
  "total": 2,
  "limit": 1,
  "offset": 0
}
```

검색결과없음:HTTP200
```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

사업검색offset2:HTTP200
```json
{
  "items": [],
  "total": 2,
  "limit": 20,
  "offset": 2
}
```

201자입력:HTTP422
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력 형식을 확인해 주세요",
    "details": []
  }
}
```
