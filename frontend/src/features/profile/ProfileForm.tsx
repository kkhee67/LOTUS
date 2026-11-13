import {useEffect, useRef, useState, type FormEvent} from 'react';
import {apiErrorMessage, canRecommend, getApi, recommend, type Capabilities, type Options, type RecommendationRequest, type RecommendationResponse} from '../../api';
import {RecommendationResults} from '../recommendations/RecommendationResults';
import {RecommendationProfile} from '../recommendations/RecommendationProfile';
import {Explore, Resources} from '../opportunities/Explore';
import {useSavedOpportunities} from '../opportunities/saved';
import {Guidance} from '../guidance/Guidance';
import {isPreview} from '../../preview';
import {workRegions} from './choices';
import {
  buildRequest, experiencePrefixes, hasAcademicYear, maxExperiences, removeExperience, splitEntries, updateExperience,
  type EducationChoice, type EmptyExperienceStatus, type ExperienceInput,
} from './profile';

const educationLabels: Record<EducationChoice, string> = {
  unknown: '선택 안 함', enrolled: '재학', leave: '휴학', graduating: '졸업 예정',
  graduated: '졸업', high_school_graduated: '고등학교 졸업', other: '해당 없음 / 기타',
};

const experienceLabels: Record<ExperienceInput['kind'], string> = {
  course_project: '수업 프로젝트', contest: '공모전·대회', club: '동아리', volunteer: '봉사',
  internship: '인턴', employment: '직장 경력', certificate: '자격증', english_test: '영어시험', other: '기타',
};

type Resource<T> = {data?: T; error?: string};
type Submission =
  | {kind: 'loading' | 'error'; message: string}
  | {kind: 'results'; response: RecommendationResponse};

const screens = {recommendations: '맞춤 추천', explore: '공고 탐색', guidance: '진로 준비', resources: '관련 사이트'} as const;
type Screen = keyof typeof screens;
const welcomeDuration = 4000;

export function ProfileForm() {
  const [stage, setStage] = useState<'welcome' | 'profile' | 'workspace'>('welcome');
  const [screen, setScreen] = useState<Screen>('recommendations');
  const [options, setOptions] = useState<Resource<Options>>({});
  const [capabilities, setCapabilities] = useState<Resource<Capabilities>>({});
  const [attempt, setAttempt] = useState(0);
  const [educationStatus, setEducationStatus] = useState<EducationChoice>('unknown');
  const [emptyExperienceStatus, setEmptyExperienceStatus] = useState<EmptyExperienceStatus>('unknown');
  const [experiences, setExperiences] = useState<ExperienceInput[]>([]);
  const [submission, setSubmission] = useState<Submission>();
  const [confirmed, setConfirmed] = useState<RecommendationRequest>();
  const [inputError, setInputError] = useState<string>();
  const saved = useSavedOpportunities();
  const requestRef = useRef<AbortController | null>(null);
  const profileHeading = useRef<HTMLHeadingElement>(null);
  const screenHeading = useRef<HTMLHeadingElement>(null);
  const experienceId = useRef(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setStage('profile'), welcomeDuration);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (stage === 'profile') profileHeading.current?.focus();
    if (stage === 'workspace') screenHeading.current?.focus();
  }, [stage, screen]);

  useEffect(() => {
    const controller = new AbortController();
    const {signal} = controller;

    function load<T>(request: Promise<T>, update: (state: Resource<T>) => void) {
      void request.then(data => {
        if (!signal.aborted) update({data});
      }).catch(error => {
        if (!signal.aborted) update({error: apiErrorMessage(error)});
      });
    }

    load(getApi<Options>('/options', signal), setOptions);
    load(getApi<Capabilities>('/capabilities', signal), setCapabilities);
    return () => {
      controller.abort();
      requestRef.current?.abort();
    };
  }, [attempt]);

  const capability = capabilities.data?.recommendations;
  const ready = canRecommend(capability);
  const loading = submission?.kind === 'loading';
  const educationChoices: EducationChoice[] = (options.data?.education_statuses ?? ['unknown', 'enrolled', 'leave', 'graduating', 'graduated', 'other'])
    .flatMap((status): EducationChoice[] => status === 'graduated' ? [status, 'high_school_graduated'] : [status]);
  const emptyExperienceChoices = (options.data?.experience_statuses ?? ['unknown', 'none'])
    .filter(status => status === 'unknown' || status === 'none');

  function clearSubmission() {
    requestRef.current?.abort();
    requestRef.current = null;
    setSubmission(undefined);
  }

  function changeProfile() {
    clearSubmission();
    setConfirmed(undefined);
    setInputError(undefined);
  }

  function retryConnection() {
    clearSubmission();
    setOptions({});
    setCapabilities({});
    setAttempt(value => value + 1);
  }

  function addExperience() {
    changeProfile();
    setEmptyExperienceStatus('unknown');
    const id = `activity-${++experienceId.current}`;
    setExperiences(items => updateExperience(items, {id, kind: 'other', title: ''}));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearSubmission();
    const {request, error} = buildRequest(
      new FormData(event.currentTarget), educationStatus, emptyExperienceStatus, experiences,
    );
    setConfirmed(request);
    setInputError(error);
  }

  function next() {
    if (!confirmed) return;
    setScreen('recommendations');
    setStage('workspace');
    if (ready && !submission) void loadRecommendations(confirmed);
  }

  async function loadRecommendations(request: RecommendationRequest) {
    clearSubmission();
    const controller = new AbortController();
    requestRef.current = controller;
    setSubmission({kind: 'loading', message: '추천 요청을 보내고 있어요.'});
    try {
      const response = await recommend(capability, request, controller.signal);
      if (!controller.signal.aborted) {
        setSubmission({kind: 'results', response});
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setSubmission({kind: 'error', message: apiErrorMessage(error)});
      }
    } finally {
      if (requestRef.current === controller) requestRef.current = null;
    }
  }

  if (stage === 'welcome') {
    return <main className="welcome-screen">
      <div className="welcome-content">
        <div className="welcome-mark" aria-hidden="true">
          <i /><i /><i /><i /><i />
        </div>
        <h1>LOTUS</h1>
        <p>환영합니다!</p>
        <div className="welcome-progress" aria-hidden="true">
          <span style={{animationDuration: `${welcomeDuration}ms`}} />
        </div>
      </div>
    </main>;
  }

  const recommendedItems = submission?.kind === 'results'
    ? submission.response.items.map(item => item.opportunity)
    : undefined;

  return (
    <>
      <header className="site-header">
        <div className="header-inner">
          <span className="wordmark">LOTUS</span>
          <span className="site-description">청년 진로·취업 안내</span>
          {stage === 'workspace' && <nav aria-label="주요 메뉴">
            {(Object.keys(screens) as Screen[]).map(value => (
              <button key={value} type="button" aria-current={screen === value ? 'page' : undefined}
                onClick={() => setScreen(value)}>{screens[value]}</button>
            ))}
          </nav>}
        </div>
      </header>
      {isPreview && <aside className="preview-banner" aria-label="테스트 모드">
        <strong>테스트 모드</strong>
        <span>고정된 임시 데이터예요. 입력은 서버로 전송되지 않아요.</span>
        <a href="/">일반 화면으로 돌아가기</a>
      </aside>}
      <main className="page" hidden={stage !== 'profile'}>
        <div className="intro">
          <h1 ref={profileHeading} tabIndex={-1}>어떤 일을 준비하고 있나요?</h1>
          <p>지금의 관심이나 목표를 알려주세요. 네 가지 중 하나만 입력해도 시작할 수 있어요.</p>
        </div>

        <form id="profile" className="profile-form" noValidate autoComplete="off" onSubmit={submit} onChange={changeProfile}>
          <section className="basic-section" aria-labelledby="basic-heading">
            <h2 id="basic-heading">기본 정보</h2>
            <div className="fields">
              <label>
                전공
                <input name="major" maxLength={200} placeholder="예: 산업디자인" />
              </label>
              <ExampleField name="interests" label="관심 분야" placeholder="예: 디자인, 데이터" choices={options.data?.fields} />
              <ExampleField name="preferred_job_fields" label="희망 직무·취업 분야" placeholder="직접 입력 예: 웹 개발자" choices={options.data?.fields} />
              <p id="entry-hint" className="field-hint">
                목록에는 추천 서버에 등록된 분야 이름과 별칭이 나와요. 목록에 없는 직무명도 직접 입력할 수 있지만,
                현재 추천에서 인식하지 못할 수 있어요. 여러 항목은 쉼표로 나눠 주세요.
              </p>
              <label className="wide">
                자유 목표
                <textarea name="goal" maxLength={4000} rows={3} placeholder="예: 다음 학기 전에 첫 포트폴리오를 만들고 싶어요." />
              </label>
            </div>
          </section>

          <details className="optional-section">
            <summary>상세 정보 <span>선택 입력</span></summary>
            <div className="fields">
              <label>
                나이
                <input name="age" inputMode="numeric" maxLength={3} placeholder="예: 24" />
              </label>
              <label>
                학교
                <input name="school_name" maxLength={200} placeholder="고등학교 또는 대학교 이름" />
              </label>
              <label>
                <span id="education-label">학적</span>
                <select aria-labelledby="education-label" value={educationStatus}
                  onChange={event => setEducationStatus(event.target.value as EducationChoice)}>
                  {educationChoices.map(status => <option key={status} value={status}>{educationLabels[status]}</option>)}
                  {!educationChoices.some(status => status === educationStatus) &&
                    <option value={educationStatus}>{educationLabels[educationStatus]}</option>}
                </select>
              </label>
              {hasAcademicYear(educationStatus) && (
                <label>
                  학년
                  <input name="academic_year" inputMode="numeric" maxLength={1} placeholder="1~8" />
                </label>
              )}
              <label>
                거주지역
                <input name="residence_region" maxLength={200} placeholder="예: 부산" />
              </label>
              <WorkRegionField onRemove={changeProfile} />
            </div>
            <fieldset className="experience-section">
              <legend>활동·경험</legend>
              {experiences.length === 0 && (
                <label>
                  <span id="experience-status-label">활동 입력 상태</span>
                  <select aria-labelledby="experience-status-label" value={emptyExperienceStatus}
                    onChange={event => setEmptyExperienceStatus(event.target.value as EmptyExperienceStatus)}>
                    {emptyExperienceChoices.map(status => (
                      <option key={status} value={status}>{status === 'unknown' ? '아직 입력하지 않음' : '활동 없음'}</option>
                    ))}
                  </select>
                </label>
              )}
              {experiences.map((entry, index) => (
                <ExperienceFields key={entry.id} entry={entry} index={index}
                  onEdit={updated => setExperiences(items => updateExperience(items, updated))}
                  onRemove={() => {
                    changeProfile();
                    setExperiences(items => removeExperience(items, entry.id));
                  }} />
              ))}
              <button type="button" className="secondary" onClick={addExperience} disabled={experiences.length >= maxExperiences}>
                활동 추가
              </button>
            </fieldset>
          </details>

          <footer className="form-footer">
            <p className="privacy-note">입력 내용은 이 화면에만 보관돼요. 자유 입력에 연락처나 학번 같은 개인정보를 적지 마세요.</p>
            {options.error && <p className="error" role="alert">선택지를 불러오지 못했어요. 기본 정보는 직접 입력할 수 있어요. {options.error}</p>}
            {inputError && <p className="error" role="alert">{inputError}</p>}
            {confirmed && <p className="feedback" role="status">입력을 확인했어요. 다음으로 이동할 수 있어요.</p>}
            <div className="actions">
              <button type="submit" className={confirmed ? 'secondary' : 'primary'}>입력 확인</button>
              {confirmed && <button type="button" className="primary" onClick={next}>다음</button>}
              {options.error && <button type="button" className="secondary" onClick={retryConnection}>연결 다시 확인</button>}
            </div>
          </footer>
        </form>
      </main>
      <main className="page" hidden={stage !== 'workspace'}>
          <div className="workspace-heading">
            <h1 ref={screenHeading} tabIndex={-1}>{screens[screen]}</h1>
            <button className="secondary" type="button" onClick={() => setStage('profile')}>입력 수정</button>
          </div>
          {screen !== 'recommendations' && !capabilities.data && (
            capabilities.error ? <div className="feature-panel">
              <p className="error" role="alert">기능 상태를 확인하지 못했어요. {capabilities.error}</p>
              <button type="button" className="secondary" onClick={retryConnection}>연결 다시 확인</button>
            </div> : <p className="availability" role="status">기능 상태를 확인하고 있어요.</p>
          )}
          <div hidden={screen !== 'recommendations'}>
            {confirmed && <RecommendationProfile profile={confirmed.profile} />}
            <RecommendationResults response={submission?.kind === 'results' ? submission.response : undefined} saved={saved}>
            {capabilities.error && <div className="feature-panel">
              <p className="error" role="alert">추천 기능 상태를 확인하지 못했어요. {capabilities.error}</p>
              <button type="button" className="secondary" onClick={retryConnection}>연결 다시 확인</button>
            </div>}
            {!ready && !capabilities.error && <p className="availability" role="status">
              {capabilities.data ? '추천 서버가 준비되면 입력한 내용에 맞는 공고를 이곳에서 확인할 수 있어요.' : '추천 기능 상태를 확인하고 있어요.'}
            </p>}
            {submission && submission.kind !== 'results' && <p className={loading ? 'feedback' : 'error'}
              role={loading ? 'status' : 'alert'}>{submission.message}</p>}
            {ready && confirmed && !loading && submission?.kind !== 'results' &&
              <button className="primary request-button" type="button" onClick={() => void loadRecommendations(confirmed)}>
                {submission?.kind === 'error' ? '추천 다시 요청' : '추천 요청 보내기'}
              </button>}
            </RecommendationResults>
          </div>
          <div hidden={screen !== 'explore' || !capabilities.data}>
            <Explore capability={capabilities.data?.opportunities} types={options.data?.opportunity_types} saved={saved}
              recommendations={recommendedItems} />
          </div>
          <div hidden={screen !== 'guidance' || !capabilities.data}>
            <Guidance key={confirmed ? 'confirmed' : 'editing'} capabilities={capabilities.data} profile={confirmed?.profile}
              opportunities={recommendedItems} />
          </div>
          <div hidden={screen !== 'resources' || !capabilities.data}>
            <Resources capability={capabilities.data?.['resource-links']} />
          </div>
      </main>
    </>
  );
}

function ExampleField({name, label, placeholder, choices}: {
  name: string;
  label: string;
  placeholder: string;
  choices?: Options['fields'];
}) {
  const [value, setValue] = useState('');
  const entries = splitEntries(value);
  return (
    <div className="choice-field">
      <label>{label}
        <input name={name} value={value} onChange={event => setValue(event.target.value)}
          placeholder={placeholder} aria-describedby="entry-hint" />
      </label>
      {Boolean(choices?.length) && <select aria-label={`${label} 등록 표현 선택`} aria-describedby="entry-hint"
        value="" onChange={event => setValue([...entries, event.target.value].join(', '))}>
        <option value="" disabled>등록된 추천 표현 선택</option>
        {choices?.map(field => <optgroup key={field.code} label={field.label}>
          {[...new Set([field.label, ...(field.aliases ?? [])])].map(choice =>
            <option key={choice} value={choice} disabled={entries.includes(choice)}>{choice}</option>,
          )}
        </optgroup>)}
      </select>}
    </div>
  );
}

function WorkRegionField({onRemove}: {onRemove: () => void}) {
  const [regions, setRegions] = useState<string[]>([]);
  return (
    <div className="choice-field">
      <label>
        <span id="work-region-label">희망 근무지역</span>
        <select aria-labelledby="work-region-label" value="" onChange={event => {
          setRegions([...regions, event.target.value]);
        }}>
          <option value="" disabled>지역 선택 · 복수 가능</option>
          {workRegions.map(region => <option key={region} value={region} disabled={regions.includes(region)}>{region}</option>)}
        </select>
      </label>
      <input type="hidden" name="preferred_job_regions" value={regions.join(',')} />
      {regions.length > 0 && <ul className="chosen-regions" aria-label="선택한 희망 근무지역">
        {regions.map(region => <li key={region}><button type="button" className="secondary"
          aria-label={`${region} 삭제`} onClick={() => {
            setRegions(regions.filter(value => value !== region));
            onRemove();
          }}>{region} ×</button></li>)}
      </ul>}
    </div>
  );
}

function ExperienceFields({entry, index, onEdit, onRemove}: {
  entry: ExperienceInput;
  index: number;
  onEdit: (entry: ExperienceInput) => void;
  onRemove: () => void;
}) {
  const prefix = entry.kind === 'certificate' || entry.kind === 'english_test' ? experiencePrefixes[entry.kind] : '';
  return (
    <fieldset className="activity">
      <legend>활동 {index + 1}</legend>
      <div className="fields">
        <label>
          <span id={`${entry.id}-kind-label`}>활동 유형</span>
          <select aria-labelledby={`${entry.id}-kind-label`} value={entry.kind}
            onChange={event => onEdit({...entry, kind: event.target.value as ExperienceInput['kind']})}>
            {Object.entries(experienceLabels).map(([kind, label]) => <option key={kind} value={kind}>{label}</option>)}
          </select>
        </label>
        <label>
          <span id={`${entry.id}-title-label`}>{entry.kind === 'certificate' ? '자격증 이름' : entry.kind === 'english_test' ? '영어시험 이름' : '활동 이름'}</span>
          <input value={entry.title} maxLength={200 - prefix.length} aria-required="true" aria-labelledby={`${entry.id}-title-label`}
            placeholder={entry.kind === 'english_test' ? '예: 토익, 토플, 오픽' : entry.kind === 'certificate' ? '예: 정보처리기능사' : undefined}
            onChange={event => onEdit({...entry, title: event.target.value})} />
        </label>
        <label className="wide">
          {entry.kind === 'english_test' ? '점수·등급 (선택)' : entry.kind === 'certificate' ? '취득일·등급 (선택)' : '활동 내용'}
          <textarea defaultValue={entry.description ?? ''} maxLength={4000} rows={2}
            onChange={event => onEdit({...entry, description: event.target.value})} />
        </label>
        <label className="wide">
          사용한 기술
          <input defaultValue={entry.skills?.join(', ')} placeholder="쉼표로 구분"
            onChange={event => onEdit({...entry, skills: splitEntries(event.target.value)})} />
        </label>
      </div>
      <button type="button" className="secondary" onClick={onRemove} aria-label={`활동 ${index + 1} 삭제`}>삭제</button>
    </fieldset>
  );
}
