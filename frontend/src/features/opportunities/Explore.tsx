import {useState} from 'react';
import {canRecommend, getList, getOpportunity, type Capability, type Opportunity, type Options} from '../../api';
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
    <OpportunityDetails opportunity={opportunity} now={new Date()} />
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
type Pages<T> = {items: T[]; total: number; next: number};

export function Explore({capability, types, saved, recommendations}: {
  capability?: Capability;
  types?: Options['opportunity_types'];
  saved: SavedOpportunities;
  recommendations?: Opportunity[];
}) {
  const [view, setView] = useState<View>('all');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<Opportunity['type'] | ''>('');
  const task = useApiTask<Pages<Opportunity>>();
  const available = canRecommend(capability);
  const pages = task.data;
  const actual = pages?.items.filter(showSource) ?? [];
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const visible = actual.filter(item => {
    if (view === 'notices' && item.type !== 'notice') return false;
    if (view === 'events' && item.type !== 'event') return false;
    if (view === 'all' && filter && item.type !== filter) return false;
    const searchable = [item.title, item.organization, item.summary, ...item.tags ?? []].join(' ').toLocaleLowerCase();
    return words.every(word => searchable.includes(word));
  });
  const cached = new Map([...actual, ...(recommendations ?? []).filter(showSource)].map(item => [item.id, item]));
  const typesToShow = types ?? Object.keys(opportunityLabels) as Opportunity['type'][];

  function load() {
    void task.run(async signal => {
      const result = await getList('opportunities', capability, pages?.next ?? 0, signal);
      return {
        items: [...new Map([...(pages?.items ?? []), ...result.items].map(item => [item.id, item])).values()],
        total: result.total,
        next: result.offset + (result.items.length || result.limit),
      };
    });
  }

  return <section id="explore" className="feature-panel" aria-label="공고 목록">
    <div className="section-switch" aria-label="공고 화면">
      {(Object.keys(views) as View[]).map(value => <button type="button" key={value} className="secondary"
        aria-pressed={view === value} onClick={() => {setView(value); setQuery('');}}>
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
        <div className="fields">
          <label>공고 검색<input type="search" value={query} onChange={event => setQuery(event.target.value)}
            placeholder="제목, 기관, 키워드" /></label>
          {view === 'all' && <label htmlFor="opportunity-filter">공고 유형
            <select id="opportunity-filter" value={filter} onChange={event => setFilter(event.target.value as typeof filter)}>
              <option value="">전체 유형</option>
              {typesToShow.map(type => <option key={type} value={type}>{opportunityLabels[type]}</option>)}
            </select>
          </label>}
        </div>
        {!available && <p className="availability">공고 조회 기능 준비 중이에요.</p>}
        {task.error && <p className="error" role="alert">{task.error}</p>}
        {pages && <p role="status">불러온 공고 {pages.items.length} / {pages.total}건 · 표시 {visible.length}건</p>}
        {pages && !visible.length && <p>불러온 목록에서 조건에 맞는 공고가 없어요.</p>}
        <div className="result-list">{visible.map(item => <OpportunityCard key={item.id} opportunity={item} saved={saved} />)}</div>
        {available && (!pages || pages.next < pages.total || task.error) &&
          <button type="button" className="secondary" onClick={load} disabled={task.loading}>
            {task.loading ? '불러오는 중…' : task.error ? '다시 시도' : pages ? '공고 더 불러오기' : '공고 불러오기'}
          </button>}
      </>
    )}
  </section>;
}

const resourceLabels = {official_site: '공식 사이트', job_board: '취업 게시판', mentoring_program: '멘토링 프로그램'};
type Resource = Awaited<ReturnType<typeof getList<'resource-links'>>>['items'][number];

export function Resources({capability}: {capability?: Capability}) {
  const task = useApiTask<Pages<Resource>>();
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
      disabled={task.loading} onClick={() => void task.run(async signal => {
        const result = await getList('resource-links', capability, pages?.next ?? 0, signal);
        return {items: [...new Map([...(pages?.items ?? []), ...result.items].map(item => [item.id, item])).values()],
          total: result.total, next: result.offset + (result.items.length || result.limit)};
      })}>
      {task.loading ? '불러오는 중…' : task.error ? '다시 시도' : pages ? '사이트 더 불러오기' : '사이트 불러오기'}
    </button>}
  </section>;
}
