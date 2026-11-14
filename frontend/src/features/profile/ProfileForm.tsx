import {useEffect, useRef, useState} from 'react';
import {canRecommend, type RecommendationRequest} from '../../api';
import {RecommendationResults} from '../recommendations/RecommendationResults';
import {RecommendationProfile} from '../recommendations/RecommendationProfile';
import {Explore} from '../opportunities/Explore';
import {SavedCalendar} from '../opportunities/SavedCalendar';
import {useSavedOpportunities} from '../opportunities/saved';
import {Guidance} from '../guidance/Guidance';
import {isPreview} from '../../preview';
import {ProfileEditor} from './ProfileEditor';
import {useServiceConnection} from '../useServiceConnection';
import {useRecommendationRequest} from '../recommendations/useRecommendationRequest';

const screens = {recommendations: '맞춤 추천', explore: '공고 탐색', calendar: '내 일정', guidance: '진로 준비'} as const;
type Screen = keyof typeof screens;
const welcomeDuration = 4000;

export function ProfileForm() {
  const [stage, setStage] = useState<'welcome' | 'profile' | 'workspace'>('welcome');
  const [screen, setScreen] = useState<Screen>('recommendations');
  const [recommendationQuery, setRecommendationQuery] = useState('');
  const {options, capabilities, reconnect} = useServiceConnection();
  const {submission, clearSubmission, loadRecommendations} = useRecommendationRequest(capabilities.data?.recommendations);
  const [confirmed, setConfirmed] = useState<RecommendationRequest>();
  const saved = useSavedOpportunities();
  const profileHeading = useRef<HTMLHeadingElement>(null);
  const screenHeading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setStage('profile'), welcomeDuration);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (stage === 'profile') profileHeading.current?.focus();
    if (stage === 'workspace') screenHeading.current?.focus();
  }, [stage, screen]);

  const capability = capabilities.data?.recommendations;
  const ready = canRecommend(capability);
  const loading = submission?.kind === 'loading';
  function changeProfile() {
    setRecommendationQuery('');
    clearSubmission();
    setConfirmed(undefined);
  }

  function retryConnection() {
    clearSubmission();
    reconnect();
  }

  function next() {
    if (!confirmed) return;
    setScreen('recommendations');
    setStage('workspace');
    if (ready && !submission) void loadRecommendations(confirmed);
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
      {isPreview && <aside className="preview-banner" aria-label="테스트 모드">
        <span>디자인 검토용 · 합성 데이터 · API 미연결</span>
        <a href="/">일반 화면으로 돌아가기</a>
      </aside>}
      <header className="site-header">
        <div className="header-inner">
          <span className="wordmark">LOTUS</span>
          {stage === 'workspace' && <nav aria-label="주요 메뉴">
            {(Object.keys(screens) as Screen[]).map(value => (
              <button key={value} type="button" aria-current={screen === value ? 'page' : undefined}
                onClick={() => setScreen(value)}>{screens[value]}</button>
            ))}
          </nav>}
          <span className="site-description">청년 진로·취업 안내</span>
          {stage === 'workspace' && <button className="secondary" type="button"
            onClick={() => setStage('profile')}>입력 수정</button>}
        </div>
      </header>
      <ProfileEditor visible={stage === 'profile'} headingRef={profileHeading} options={options}
        confirmed={confirmed} onConfirm={request => {clearSubmission(); setConfirmed(request);}}
        onChange={changeProfile} onNext={next} retryConnection={retryConnection} />
      <main className="page" hidden={stage !== 'workspace'}>
          <div className="workspace-heading">
            <div>
              {screen === 'recommendations' && !!confirmed?.profile.interests?.length &&
                <p className="interest-line">관심 분야 · {confirmed.profile.interests.join(' / ')}</p>}
              <h1 ref={screenHeading} tabIndex={-1}>{screen === 'recommendations' ? '나에게 맞는 기회' : screens[screen]}</h1>
              {screen === 'recommendations' && <p className="hero-description">공고를 비교하고, 나의 다음 경험을 찾아보세요.</p>}
              {screen === 'calendar' && <p className="hero-description">별표로 저장한 공고의 접수·행사·시험 일정을 확인하세요.</p>}
            </div>
            {screen === 'recommendations' && <label className="recommendation-search">추천 목록에서 찾기
              <input type="search" value={recommendationQuery} placeholder="제목·기관·태그 검색"
                onChange={event => setRecommendationQuery(event.target.value)} />
            </label>}
          </div>
          {screen !== 'recommendations' && !capabilities.data && (
            capabilities.error ? <div className="feature-panel">
              <p className="error" role="alert">기능 상태를 확인하지 못했어요. {capabilities.error}</p>
              <button type="button" className="secondary" onClick={retryConnection}>연결 다시 확인</button>
            </div> : <p className="availability" role="status">기능 상태를 확인하고 있어요.</p>
          )}
          <div hidden={screen !== 'recommendations'}>
            {confirmed && <details className="profile-disclosure"><summary>내 진로와 준비 경험</summary>
              <RecommendationProfile profile={confirmed.profile} />
            </details>}
            <RecommendationResults response={submission?.kind === 'results' ? submission.response : undefined}
              query={recommendationQuery} saved={saved}>
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
            <Explore active={screen === 'explore'} capability={capabilities.data?.opportunities} types={options.data?.opportunity_types} saved={saved}
              recommendations={submission?.kind === 'results' ? submission.response.items : undefined} />
          </div>
          <div hidden={screen !== 'guidance' || !capabilities.data}>
            <Guidance key={confirmed ? 'confirmed' : 'editing'} capabilities={capabilities.data} profile={confirmed?.profile}
              opportunities={recommendedItems} />
          </div>
          {stage === 'workspace' && screen === 'calendar' && capabilities.data &&
            <SavedCalendar saved={saved} capability={capabilities.data.opportunities}
              fields={options.data?.fields} profileInterests={confirmed?.profile.interests} />}
      </main>
    </>
  );
}
