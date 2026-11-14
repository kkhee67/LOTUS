import {useState, type ReactNode} from 'react';
import type { components } from '../../generated/api';
import type { Opportunity, RecommendationResponse } from '../../api';
import type { SavedOpportunities } from '../opportunities/saved';
import {OpportunityPoster} from '../opportunities/OpportunityPoster';
import {showSource} from '../../preview';
import {applicationStatus, closesToday, deadlineLabel, sourceHref} from './presentation';
import {useApplicationClock} from './useApplicationClock';
import {certificationRequirements, inCategory, languageRequirements, recommendationCategories, researchRequirements, type RecommendationCategory} from './categories';

type Item = RecommendationResponse['items'][number];
type Application = components['schemas']['ApplicationInfo'];

export const opportunityLabels: Record<Opportunity['type'], string> = {
  contest: '공모전', competition: '경진대회', job: '채용', certification: '자격증',
  event: '행사', training: '교육', project: '프로젝트', notice: '공지',
};
const eligibilityLabels: Record<Item['recommendation']['eligibility'], string> = {
  eligible: '입력 기준 충족 · 원문 확인',
  ineligible: '입력 기준 일부 불충족',
  unknown: '추가 확인 필요',
};
const applicationLabels: Record<Application['status'], string> = {
  open: '접수 중', upcoming: '접수 예정', closed: '접수 마감', unknown: '접수 상태 미확인',
};
const certificationLabels = {active: '운영 중', inactive: '운영 종료', unknown: '운영 상태 미확인'};
const seoulTime = new Intl.DateTimeFormat('ko-KR', {
  timeZone: 'Asia/Seoul', dateStyle: 'medium', timeStyle: 'short',
});

export function displayDate(day?: string | null, instant?: string | null): string | undefined {
  if (day) return day;
  if (instant && Number.isFinite(Date.parse(instant))) return `${seoulTime.format(new Date(instant))} (한국 시간)`;
}

export function TextList({items}: {items: string[]}) {
  return <ul>{items.map((text, index) => <li key={index}>{text}</li>)}</ul>;
}

function ApplicationDates({application}: {application?: Application}) {
  const now = useApplicationClock(application);
  if (!application) return <p>접수 상태 미확인</p>;
  const start = displayDate(application.opens_on, application.opens_at);
  const end = displayDate(application.closes_on, application.closes_at);
  return (
    <div>
      <p>{applicationLabels[applicationStatus(application, now)]}</p>
      {start && <p>접수 시작 · {start}</p>}
      {end && <p>접수 마감 · {end}</p>}
      {closesToday(application, now) && <p>마감일 당일입니다. 정확한 마감 시각은 원문에서 확인하세요.</p>}
    </div>
  );
}

export function opportunityType(opportunity: Opportunity): string {
  if (opportunity.type === 'job' && opportunity.subtype === 'internship') return '인턴';
  if (opportunity.type === 'event' && opportunity.subtype === 'briefing') return '설명회';
  if (opportunity.type === 'event' && opportunity.subtype === 'job_fair') return '취업 박람회';
  return opportunityLabels[opportunity.type];
}

export function SaveOpportunity({opportunity, saved, score}: {opportunity: Opportunity; saved: SavedOpportunities; score?: number}) {
  const sessions = opportunity.certification?.exam_sessions;
  const now = useApplicationClock(opportunity.application, sessions);
  const nextSession = sessions?.map(session => session.application)
    .filter((a): a is Application => !!a && applicationStatus(a, now) !== 'closed' && !!(a.closes_on || a.closes_at))
    .sort((a, b) => Date.parse(a.closes_at ?? a.closes_on + 'T23:59:59.999+09:00')
      - Date.parse(b.closes_at ?? b.closes_on + 'T23:59:59.999+09:00'))[0];
  const countdown = opportunity.type === 'certification'
    ? nextSession ? '회차 ' + deadlineLabel(nextSession, now) : '회차 마감일 미확인'
    : deadlineLabel(opportunity.application, now);
  if (!showSource(opportunity)) return null;
  const selected = saved.ids.includes(opportunity.id);
  return <div className="save-metrics"><button type="button" className="bookmark-star" aria-label="관심 공고 저장" title={selected ? "관심 공고 저장 해제" : "관심 공고 저장"} aria-pressed={selected}
    onClick={() => saved.toggle(opportunity.id)}>{selected ? '★' : '☆'}</button>
    <span className="relevance-value">관련성 {score === undefined ? '점수 미제공' : score + '점'}</span>
    <span className="deadline-value">{countdown}</span>
  </div>;
}

function RecommendationCard({item, saved, category}: {
  item: Item; saved: SavedOpportunities; category: RecommendationCategory;
}) {
  const {recommendation, opportunity} = item;
  const now = useApplicationClock(opportunity.application);
  const cautions = [...new Set([...(recommendation.cautions ?? []), ...(opportunity.unresolved_conditions ?? [])])];
  const published = displayDate(opportunity.published_on, opportunity.published_at);
  const deadline = displayDate(opportunity.application?.closes_on, opportunity.application?.closes_at);
  const qualifications = category === 'certifications' ? certificationRequirements(opportunity) : [];
  const research = category === 'research' ? researchRequirements(opportunity) : [];
  return (
    <li className="result-card recommendation-card">
      <OpportunityPoster item={opportunity} label={opportunityType(opportunity)} />
      <p className="result-meta"><strong className="type-label">{opportunityType(opportunity)}</strong> {opportunity.organization}</p>
      <h3>{opportunity.title}</h3>
      <p className="application-line">
        {opportunity.certification ? certificationLabels[opportunity.certification.status]
          : opportunity.application ? applicationLabels[applicationStatus(opportunity.application, now)] : '접수 상태 미확인'}
      </p>
      {opportunity.source_kind === 'synthetic' && <p className="availability">연습용 자료</p>}
      {(opportunity.type === 'notice' || opportunity.type === 'event') && (
        <dl className="result-facts">
          {published && <div><dt>게시일</dt><dd>{published}</dd></div>}
          {opportunity.event_schedule?.starts_on &&
            <div><dt>행사일</dt><dd>{opportunity.event_schedule.starts_on}</dd></div>}
          {deadline && <div><dt>접수 마감</dt><dd>{deadline}</dd></div>}
        </dl>
      )}
      <dl className="result-facts">
        <div><dt>지원 자격</dt><dd>{eligibilityLabels[recommendation.eligibility]}</dd></div>
      </dl>
      {recommendation.reasons[0] && <p className="reason-highlight">{recommendation.reasons[0].text}</p>}
      {!!opportunity.tags?.length && <ul className="opportunity-tags" aria-label="공고 태그">
        {opportunity.tags.map(tag => <li key={tag}>{tag}</li>)}
      </ul>}
      <SaveOpportunity opportunity={opportunity} saved={saved} score={recommendation.relevance_score} />
      <details className="reason-details">
        <summary>추천 이유·확인 사항</summary>
        <h4>추천 이유</h4>
        {recommendation.reasons.length ? <TextList items={recommendation.reasons.map(reason => reason.text)} />
          : <p>제공된 추천 이유가 없어요.</p>}
        <h4>지원 전 확인 사항</h4>
        {cautions.length > 0 ? <TextList items={cautions} /> : <p>지원 조건과 일정을 원문에서 확인하세요.</p>}
        {category === 'languages' && <>
          <h4>공고에 적힌 어학 조건</h4>
          <TextList items={languageRequirements(opportunity)} />
        </>}
        {qualifications.length > 0 && <>
          <h4>공고에 적힌 자격증 조건</h4>
          <TextList items={qualifications} />
        </>}
        {research.length > 0 && <>
          <h4>공고에 적힌 학위·연구 조건</h4>
          <TextList items={research} />
        </>}
      </details>
      <OpportunityDetails opportunity={opportunity} />
    </li>
  );
}

export function OpportunityDetails({opportunity}: {opportunity: Opportunity}) {
  const {certification, event_schedule: event} = opportunity;
  const url = opportunity.source_kind === 'real' ? sourceHref(opportunity.source_url) : undefined;
  const published = displayDate(opportunity.published_on, opportunity.published_at);
  const checked = displayDate(null, opportunity.checked_at);
  return (
      <details className="result-details">
        <summary aria-label={`${opportunity.title} 상세 보기`}>상세 보기</summary>
        {opportunity.type === 'certification' && <h4>자격증 소개</h4>}
        <p>{opportunity.summary}</p>
        {Boolean(opportunity.requirements?.length) && (
          <><h4>준비 요건</h4><TextList items={opportunity.requirements ?? []} /></>
        )}
        {Boolean(opportunity.eligibility_rules?.length) && (
          <><h4>공고에 적힌 지원 조건</h4><TextList items={opportunity.eligibility_rules?.map(rule => rule.summary) ?? []} /></>
        )}
        {opportunity.type === 'certification' ? (
          certification ? (
            <>
              <h4>자격증 운영 정보</h4>
              <p>{certification.issuer} · {certificationLabels[certification.status]}</p>
              <h4>시험 회차별 접수 일정</h4>
              {certification.exam_sessions?.length ? (
                <ul className="exam-sessions">{certification.exam_sessions.map(session => (
                  <li key={session.id}>
                    <strong>{session.name}</strong>
                    <ApplicationDates application={session.application} />
                    {session.exam_on && <p>시험일 · {session.exam_on}</p>}
                    {session.schedule_note && <p>{session.schedule_note}</p>}
                  </li>
                ))}</ul>
              ) : <p>확인된 시험 회차가 없어요.</p>}
            </>
          ) : <p>자격증 운영 정보와 시험 회차를 확인할 수 없어요.</p>
        ) : (
          <><h4>접수 일정</h4><ApplicationDates application={opportunity.application} /></>
        )}
        {event && (
          <>
            <h4>행사 일정</h4>
            {event.starts_on && <p>개최일 · {event.starts_on}</p>}
            {event.ends_on && <p>종료일 · {event.ends_on}</p>}
            {event.note && <p>{event.note}</p>}
          </>
        )}
        {published && <p>게시일 · {published}</p>}
        {checked && <p>마지막 자료 확인 · {checked}</p>}
        {url ? <a href={url} target="_blank" rel="noopener noreferrer">공고 원문 열기 (새 탭)</a>
          : <p>열 수 있는 공고 원문이 없어요.</p>}
      </details>
  );
}

export function RecommendationResults({response, query, saved, children}: {
  response?: RecommendationResponse;
  query: string;
  saved: SavedOpportunities;
  children: ReactNode;
}) {
  const [category, setCategory] = useState<RecommendationCategory>('all');
  const items = response?.items;
  const categories = Object.keys(recommendationCategories) as RecommendationCategory[];
  const terms = query.normalize('NFKC').trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const matches = items?.filter(({opportunity}) => {
    const text = [opportunity.title, opportunity.organization, ...(opportunity.tags ?? [])]
      .join(' ').normalize('NFKC').toLocaleLowerCase();
    return terms.every(term => text.includes(term));
  });
  const visible = matches?.filter(item => inCategory(item.opportunity, category));
  return (
    <section className="results" aria-labelledby="results-heading">
      <h2 id="results-heading">추천 결과</h2>
      <div className="section-switch recommendation-categories" role="group" aria-label="추천 분야">
        {categories.map(value => <button type="button" className="secondary" key={value}
          aria-pressed={category === value} onClick={() => setCategory(value)}>
          {recommendationCategories[value]}{items && (
            <span className="category-count">{matches?.filter(item => inCategory(item.opportunity, value)).length}</span>
          )}
        </button>)}
      </div>
      {category === 'languages' && <p>공고마다 어학 기준이 달라요. 공고에 명시된 시험과 기준을 확인할 수 있어요.</p>}
      {category === 'research' && <p>학부연구생·연구 인턴·대학원 모집과 학위·연구 조건이 적힌 공고를 모아 볼 수 있어요.</p>}
      {children}
      {visible && <p role="status">{terms.length > 0 && !visible.length ? '검색어에 맞는 추천이 없어요.' : category === 'all' && !visible.length
        ? '조건에 맞는 추천이 없어요. 관심 분야나 목표를 바꿔 다시 시도해 보세요.'
        : visible.length ? `추천 ${visible.length}건을 찾았어요.`
        : `${recommendationCategories[category]}에 해당하는 추천이 없어요.`}</p>}
      {response && response.candidate_count > response.items.length &&
        <p>전체 추천 후보 {response.candidate_count}건 중 {response.items.length}건을 받았어요.</p>}
      {Boolean(response?.warnings?.length) && <TextList items={response?.warnings ?? []} />}
      {Boolean(visible?.length) && <ul className="result-list">
        {visible?.map(item => <RecommendationCard key={item.opportunity.id} item={item}
          saved={saved} category={category} />)}
      </ul>}
    </section>
  );
}
