import {OpportunityPoster} from './OpportunityPoster';
import {usePaginatedList} from './usePaginatedList';
import {useEffect, useRef, useState, type FormEvent} from 'react';
import {canRecommend, getList, getOpportunity, maxOpportunityQueryLength, type Capability, type Opportunity, type RecommendationResponse, type OpportunitySearch, type Options} from '../../api';
import {displayDate, OpportunityDetails, opportunityLabels, opportunityType, SaveOpportunity} from '../recommendations/RecommendationResults';
import {applicationStatus, sourceHref} from '../recommendations/presentation';
import {useApiTask} from '../useApiTask';
import {showSource} from '../../preview';
import type {SavedOpportunities} from './saved';

function OpportunityCard({opportunity, saved, score}: {opportunity: Opportunity; saved: SavedOpportunities; score?: number}) {
  return <article className="result-card explore-card">
    <OpportunityPoster item={opportunity} label={opportunityType(opportunity)} />
    <div className="explore-card-copy">
    <p className="result-meta">{opportunityType(opportunity)} · {opportunity.organization}</p>
    <h3>{opportunity.title}</h3>
    {opportunity.source_kind === 'synthetic' && <p className="availability">테스트용 공고</p>}
    <SaveOpportunity opportunity={opportunity} saved={saved} score={score} />
    <OpportunityDetails opportunity={opportunity} />
    </div>
  </article>;
}

function SavedCard({id, cached, capability, saved, score}: {
  id: string; score?: number; cached?: Opportunity; capability?: Capability; saved: SavedOpportunities;
}) {
  const task = useApiTask<Opportunity>();
  const opportunity = cached ?? task.data;
  if (opportunity && showSource(opportunity)) return <OpportunityCard opportunity={opportunity} saved={saved} score={score} />;
  return <div className="result-card">
    <p>{canRecommend(capability) ? '저장한 공고의 정보를 불러올 수 있어요.' : '공고 조회 기능이 준비되면 상세 정보를 볼 수 있어요.'}</p>
    {task.error && <p role="alert" className="error">{task.error}</p>}
    {task.data?.source_kind === 'synthetic' && <p>현재 확인할 수 있는 실제 공고가 없어요.</p>}
    <div className="actions">
      {canRecommend(capability) && <button type="button" className="secondary" disabled={task.loading}
        onClick={() => void task.run(signal => getOpportunity(id, capability, signal))}>
        {task.loading ? '불러오는 중…' : task.error ? '다시 시도' : '공고 불러오기'}
      </button>}
      <button type="button" className="secondary" onClick={() => saved.toggle(id)}>저장 해제</button>
    </div>
  </div>;
}

const views = {all: '전체 공고', notices: '일반 안내', events: '행사·설명회·박람회', saved: '관심 공고'} as const;
type View = keyof typeof views;

const pageSize = 8;
type Sort = 'deadline' | 'score' | 'latest';

function deadline(item: Opportunity, now: Date) {
  const schedules = item.certification ? item.certification.exam_sessions?.map(x => x.application) ?? [] : [item.application];
  let nearest = Infinity;
  for (const a of schedules) {
    if (!a || applicationStatus(a, now) === 'closed') continue;
    const end = a.closes_at ?? (a.closes_on && a.closes_on + 'T23:59:59.999+09:00');
    if (end) nearest = Math.min(nearest, Date.parse(end));
  }
  return nearest;
}

function published(item: Opportunity) {
  const date = item.published_at ?? (item.published_on && item.published_on + 'T00:00:00+09:00');
  return date ? Date.parse(date) : -Infinity;
}

function PageNumbers({page, count, position, select}: {
  page: number; count: number; position: string; select: (n: number) => void;
}) {
  const numbers = Array.from({length: count}, (_, i) => i + 1)
    .filter(n => n === 1 || n === count || Math.abs(n - page) <= 1);
  return <nav className="page-numbers" aria-label={position + ' 페이지 이동'}>
    <button type="button" disabled={page === 1} onClick={() => select(page - 1)}>이전</button>
    {numbers.map((n, i) => <span key={n}>
      {i > 0 && n - numbers[i - 1] > 1 && <span aria-hidden="true">…</span>}
      <button type="button" aria-label={n + '페이지'} aria-current={page === n ? 'page' : undefined}
        onClick={() => select(n)}>{n}</button>
    </span>)}
    <button type="button" disabled={page === count} onClick={() => select(page + 1)}>다음</button>
  </nav>;
}

export function Explore({active, capability, types, saved, recommendations}: {
  capability?: Capability;
  active: boolean;
  types?: Options['opportunity_types'];
  saved: SavedOpportunities;
  recommendations?: RecommendationResponse['items'];
}) {
  const [view, setView] = useState<View>('all');
  const [draftQuery, setDraftQuery] = useState('');
  const [queryError, setQueryError] = useState('');
  const [filter, setFilter] = useState<Opportunity['type'] | ''>('');
  const [search, setSearch] = useState<OpportunitySearch>({});
  const composing = useRef(false);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<Sort>('deadline');
  const [retry, setRetry] = useState(0);
  const task = useApiTask<Opportunity[]>();
  const {run, reset} = task;
  const available = canRecommend(capability);
  useEffect(() => {
    if (!active || !available || view === 'saved') return;
    reset();
    void run(async signal => {
      const items: Opportunity[] = [];
      let offset = 0;
      do {
        const batch = await getList('opportunities', capability, offset, signal, {...search, limit: 100});
        items.push(...batch.items);
        offset += batch.items.length;
        if (!batch.items.length || offset >= batch.total) break;
      } while (!signal.aborted);
      return items.filter(showSource);
    });
  }, [active, available, capability, search, view, run, reset, retry]);
  const actual = task.data ?? [];
  const scores = new Map(recommendations?.map(item => [item.opportunity.id, item.recommendation.relevance_score]));
  const cached = new Map([...actual, ...(recommendations ?? []).map(item => item.opportunity).filter(showSource)].map(item => [item.id, item]));
  const typesToShow = types ?? Object.keys(opportunityLabels) as Opportunity['type'][];

  const now = new Date();
  const ordered = actual.map(item => ({item, key: sort === 'deadline' ? deadline(item, now)
    : sort === 'latest' ? -published(item) : -(scores.get(item.id) ?? -Infinity)}))
    .sort((a, b) => a.key - b.key || a.item.id.localeCompare(b.item.id));
  const count = Math.ceil((view === 'saved' ? saved.ids.length : ordered.length) / pageSize);
  const current = Math.min(page, Math.max(1, count));
  const first = (current - 1) * pageSize;
  const pager = (position: string) => count > 0 && <PageNumbers page={current} count={count}
    position={position} select={n => {setPage(n); if (position === '하단') document.querySelector('#explore')?.scrollIntoView();}} />;
  function startSearch(criteria: OpportunitySearch) {
    setSearch(criteria);
    setQueryError('');
    setPage(1);
  }

  function changeView(nextView: View) {
    if (nextView === view) return;
    setView(nextView);
    setDraftQuery('');
    setFilter('');
    startSearch({types: nextView === 'notices' ? ['notice'] : nextView === 'events' ? ['event'] : []});
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (composing.current || !available) return;
    const q = draftQuery.trim();
    if (Array.from(q).length > maxOpportunityQueryLength) {
      setQueryError('검색어를 200자 이내로 입력해 주세요.');
      return;
    }
    startSearch({...search, q});
  }

  return <section id="explore" className="feature-panel" aria-label="공고 목록">
    <div className="section-switch" aria-label="공고 화면">
      {(Object.keys(views) as View[]).map(value => <button type="button" key={value} className="secondary"
        aria-pressed={view === value} onClick={() => changeView(value)}>
        {views[value]}{value === 'saved' && saved.ids.length > 0 ? ` (${saved.ids.length})` : ''}
      </button>)}
    </div>
    {saved.storageError && <p className="error" role="alert">이 브라우저에 관심 공고를 보관할 수 없어요. 현재 화면에서만 유지돼요.</p>}
    {view === 'saved' ? (
      saved.ids.length ? <>{pager('상단')}<div className="result-list">{saved.ids.slice(first, first + pageSize).map(id =>
        <SavedCard key={id} id={id} score={scores.get(id)} cached={cached.get(id)} capability={capability} saved={saved} />,
      )}</div>{pager('하단')}</> : <p>저장한 관심 공고가 없어요.</p>
    ) : (
      <>
        <form className="fields" onSubmit={submitSearch}>
          <label>공고 검색<input type="search" value={draftQuery} onChange={event => {
            setDraftQuery(event.target.value);
            setQueryError('');
          }} aria-describedby="opportunity-search-hint" aria-invalid={Boolean(queryError)}
            onCompositionStart={() => {composing.current = true;}}
            onCompositionEnd={() => {composing.current = false;}}
            onKeyDown={event => {
              if (event.key === 'Enter' && (event.nativeEvent.isComposing || composing.current)) event.preventDefault();
            }}
            placeholder="제목, 기관, 키워드" /></label>
          {view === 'all' && <label htmlFor="opportunity-filter">공고 유형
            <select id="opportunity-filter" value={filter} onChange={event => {
              const type = event.target.value as typeof filter;
              setFilter(type);
              startSearch({...search, types: type ? [type] : []});
            }}>
              <option value="">전체 유형</option>
              {typesToShow.map(type => <option key={type} value={type}>{opportunityLabels[type]}</option>)}
            </select>
          </label>}
          <label htmlFor="publisher-filter">게시 출처
            <select id="publisher-filter" value={search.publisher ?? ''} onChange={event =>
              startSearch({...search, publisher: event.target.value as OpportunitySearch['publisher'] || undefined})}>
              <option value="">전체 출처</option>
              <option value="school">학교 공고</option>
              <option value="official">기관·주최 측 공식 공고</option>
              <option value="aggregator">공고 모음 사이트</option>
            </select>
          </label>
          <p id="opportunity-search-hint" className="field-hint">검색어는 검색 버튼을 눌러 적용하세요. 유형과 출처는 선택 즉시 적용돼요.</p>
          <div className="search-order">
            <button type="submit" className="primary" disabled={!available}>검색</button>
            <select aria-label="정렬 기준" value={sort} onChange={e => {setSort(e.target.value as Sort); setPage(1);}}>
              <option value="deadline">마감 날짜순</option><option value="score">관련성 점수 높은순</option>
              <option value="latest">최신순</option>
            </select>
          </div>
        </form>
        {queryError && <p className="error" role="alert">{queryError}</p>}
        {!available && <p className="availability">공고 조회 기능 준비 중이에요.</p>}
        {task.error && <p className="error" role="alert">{task.error}</p>}
        {task.loading && <p role="status">공고를 불러오는 중…</p>}
        {task.error && <button type="button" onClick={() => setRetry(retry + 1)}>다시 시도</button>}
        {task.data && <p role="status">검색 결과 {actual.length}건{search.q && ' · ' + search.q}</p>}
        {task.data && !actual.length && <p>검색 조건에 맞는 공고가 없어요.</p>}
        {pager('상단')}
        <div className="result-list">{ordered.slice(first, first + pageSize).map(({item}) =>
          <OpportunityCard key={item.id} opportunity={item} saved={saved} score={scores.get(item.id)} />)}</div>
        {pager('하단')}
      </>
    )}
  </section>;
}

const resourceLabels = {official_site: '공식 사이트', job_board: '취업 게시판', mentoring_program: '멘토링 프로그램'};
type Resource = Awaited<ReturnType<typeof getList<'resource-links'>>>['items'][number];

export function Resources({capability}: {capability?: Capability}) {
  const task = usePaginatedList<Resource>((offset, signal) => getList('resource-links', capability, offset, signal));
  const pages = task.data;
  const actual = pages?.items.filter(showSource) ?? [];
  const available = canRecommend(capability);

  return <section id="resources" className="feature-panel" aria-label="관련 사이트 목록">
    {!available && <p className="availability">관련 사이트 조회 기능 준비 중이에요.</p>}
    {task.error && <p className="error" role="alert">{task.error}</p>}
    {pages && !actual.length && <p>확인된 관련 사이트가 없어요.</p>}
    {actual.length > 0 && <ul className="result-list">{actual.map(item => {
      const href = item.source_kind === 'real' ? sourceHref(item.url) : undefined;
      return <li className="result-card" key={item.id}>
        <p className="result-meta">{resourceLabels[item.kind]}</p>
        <h3>{item.name}</h3><p>{item.description}</p>
        <p>마지막 자료 확인 · {displayDate(null, item.checked_at) ?? '미확인'}</p>
        {href ? <a href={href} target="_blank" rel="noopener noreferrer">사이트 열기 (새 탭)</a>
          : item.source_kind === 'synthetic' && <p>테스트용 사이트 카드</p>}
      </li>;
    })}</ul>}
    {available && (!pages || pages.next < pages.total || task.error) && <button className="secondary" type="button"
      disabled={task.loading} onClick={() => void task.load()}>
      {task.loading ? '불러오는 중…' : task.error ? '다시 시도' : pages ? '사이트 더 불러오기' : '사이트 불러오기'}
    </button>}
  </section>;
}
