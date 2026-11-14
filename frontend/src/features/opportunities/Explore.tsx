import {usePaginatedList} from './usePaginatedList';
import {useRef, useState, type FormEvent} from 'react';
import {canRecommend, getList, getOpportunity, maxOpportunityQueryLength, type Capability, type Opportunity, type OpportunitySearch, type Options} from '../../api';
import {displayDate, OpportunityDetails, opportunityLabels, opportunityType, SaveOpportunity} from '../recommendations/RecommendationResults';
import {sourceHref} from '../recommendations/presentation';
import {useApiTask} from '../useApiTask';
import {showSource} from '../../preview';
import type {SavedOpportunities} from './saved';

function OpportunityCard({opportunity, saved}: {opportunity: Opportunity; saved: SavedOpportunities}) {
  return <article className="result-card">
    <p className="result-meta">{opportunityType(opportunity)} · {opportunity.organization}</p>
    <h3>{opportunity.title}</h3>
    {opportunity.source_kind === 'synthetic' && <p className="availability">테스트용 공고</p>}
    <SaveOpportunity opportunity={opportunity} saved={saved} />
    <OpportunityDetails opportunity={opportunity} />
  </article>;
}

function SavedCard({id, cached, capability, saved}: {
  id: string; cached?: Opportunity; capability?: Capability; saved: SavedOpportunities;
}) {
  const task = useApiTask<Opportunity>();
  const opportunity = cached ?? task.data;
  if (opportunity && showSource(opportunity)) return <OpportunityCard opportunity={opportunity} saved={saved} />;
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

const views = {all: '전체 공고', notices: '학교·기관 공지', events: '설명회·박람회', saved: '관심 공고'} as const;
type View = keyof typeof views;

export function Explore({capability, types, saved, recommendations}: {
  capability?: Capability;
  types?: Options['opportunity_types'];
  saved: SavedOpportunities;
  recommendations?: Opportunity[];
}) {
  const [view, setView] = useState<View>('all');
  const [draftQuery, setDraftQuery] = useState('');
  const [queryError, setQueryError] = useState('');
  const [filter, setFilter] = useState<Opportunity['type'] | ''>('');
  const [search, setSearch] = useState<OpportunitySearch>({});
  const composing = useRef(false);
  const fetchPage = (criteria: OpportunitySearch) => (offset: number, signal: AbortSignal) =>
    getList('opportunities', capability, offset, signal, criteria);
  const task = usePaginatedList<Opportunity>(fetchPage(search));
  const available = canRecommend(capability);
  const pages = task.data;
  const actual = pages?.items.filter(showSource) ?? [];
  const cached = new Map([...actual, ...(recommendations ?? []).filter(showSource)].map(item => [item.id, item]));
  const typesToShow = types ?? Object.keys(opportunityLabels) as Opportunity['type'][];

  function startSearch(criteria: OpportunitySearch, nextView = view) {
    setSearch(criteria);
    setQueryError('');
    if (available && nextView !== 'saved') void task.restart(fetchPage(criteria));
    else task.reset();
  }

  function changeView(nextView: View) {
    if (nextView === view) return;
    setView(nextView);
    setDraftQuery('');
    setFilter('');
    startSearch({types: nextView === 'notices' ? ['notice'] : nextView === 'events' ? ['event'] : []}, nextView);
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
      saved.ids.length ? <div className="result-list">{saved.ids.map(id =>
        <SavedCard key={id} id={id} cached={cached.get(id)} capability={capability} saved={saved} />,
      )}</div> : <p>저장한 관심 공고가 없어요.</p>
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
          <p id="opportunity-search-hint" className="field-hint">검색어는 검색 버튼을 눌러 적용하세요. 공고 유형은 선택 즉시 적용돼요.</p>
          <div className="actions">
            <button type="submit" className="primary" disabled={!available}>검색</button>
          </div>
        </form>
        {queryError && <p className="error" role="alert">{queryError}</p>}
        {!available && <p className="availability">공고 조회 기능 준비 중이에요.</p>}
        {task.error && <p className="error" role="alert">{task.error}</p>}
        {pages && <p role="status">불러온 공고 {pages.items.length} / {pages.total}건 · 표시 {actual.length}건
          {search.q && <> · 검색어: {search.q}</>}</p>}
        {pages && !pages.total && <p>검색 조건에 맞는 공고가 없어요.</p>}
        <div className="result-list">{actual.map(item => <OpportunityCard key={item.id} opportunity={item} saved={saved} />)}</div>
        {available && (!pages || pages.next < pages.total || task.error) &&
          <button type="button" className="secondary" onClick={() => void task.load()} disabled={task.loading}>
            {task.loading ? pages ? '공고 더 불러오는 중…' : '검색 결과 불러오는 중…'
              : task.error ? '다시 시도' : pages ? '공고 더 불러오기' : '공고 불러오기'}
          </button>}
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
