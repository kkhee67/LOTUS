import {useEffect, useState} from 'react';
import {canRecommend, getOpportunity, type Capability, type Opportunity, type Options} from '../../api';
import {interestExamples} from '../profile/choices';
import {showSource} from '../../preview';
import {useApiTask} from '../useApiTask';
import {OpportunityDetails} from '../recommendations/RecommendationResults';
import {seoulDate} from '../recommendations/presentation';
import type {SavedOpportunities} from './saved';

type Entry = {item: Opportunity; label: string; start: string; end: string};
const weekdays = ['일', '월', '화', '수', '목', '금', '토'];

function calendarEntries(item: Opportunity) {
  const entries: Entry[] = [];
  function add(label: string, start?: string | null, end?: string | null) {
    if (start) entries.push({item, label, start, end: end || start});
  }
  function applicationDates(application: Opportunity['application'], prefix = '') {
    if (!application) return;
    const {opens_on, opens_at, closes_on, closes_at} = application;
    add(prefix + '접수 시작', opens_on ?? (opens_at && seoulDate.format(new Date(opens_at))));
    add(prefix + '접수 마감', closes_on ?? (closes_at && seoulDate.format(new Date(closes_at))));
  }
  applicationDates(item.application);
  const event = item.event_schedule;
  if (event?.starts_on) add('행사', event.starts_on, event.ends_on);
  else add('행사 종료', event?.ends_on);
  for (const session of item.certification?.exam_sessions ?? []) {
    applicationDates(session.application, session.name + ' · ');
    add(session.name + ' · 시험', session.exam_on);
  }
  return entries;
}

function normalizeTerm(text: string) {
  return text.normalize('NFKC').trim().toLowerCase();
}

function matchesInterest(item: Opportunity, interest: string, fields: Options['fields']) {
  const field = fields.find(option => [option.code, option.label, ...(option.aliases ?? [])]
    .some(alias => normalizeTerm(alias) === normalizeTerm(interest)));
  if (field && item.fields?.includes(field.code)) return true;
  const terms = (field ? [field.label, ...(field.aliases ?? [])] : [interest])
    .flatMap(term => term.split('·')).map(normalizeTerm).filter(Boolean);
  const text = normalizeTerm([item.title, item.summary, ...(item.tags ?? []), ...(item.activities ?? []),
    ...(item.related_majors ?? [])].join(' '));
  return terms.some(term => text.includes(term));
}

export function SavedCalendar({saved, capability, fields = [], profileInterests = []}: {
  saved: SavedOpportunities; capability?: Capability; fields?: Options['fields']; profileInterests?: string[];
}) {
  const today = seoulDate.format(new Date());
  const [month, setMonth] = useState(today.slice(0, 7));
  const [selected, setSelected] = useState('');
  const [interests, setInterests] = useState<string[]>([]);
  const choices = [...new Set([...profileInterests,
    ...fields.flatMap(field => [field.label, ...(field.aliases ?? [])]), ...interestExamples])];
  const [retry, setRetry] = useState(0);
  const {ids} = saved;
  const {run, data, loading, error} = useApiTask<{items: Opportunity[]; missing: string[]}>();
  const available = canRecommend(capability);
  useEffect(() => {
    if (!available || !ids.length) return;
    void run(async signal => {
      const items: Opportunity[] = [];
      const missing: string[] = [];
      for (let i = 0; i < ids.length && !signal.aborted; i += 6) {
        const batch = ids.slice(i, i + 6);
        const results = await Promise.allSettled(batch.map(id => getOpportunity(id, capability, signal)));
        results.forEach((result, index) => {
          if (result.status === 'fulfilled' && showSource(result.value)) items.push(result.value);
          else missing.push(batch[index]);
        });
      }
      return {items, missing};
    });
  }, [available, capability, ids, retry, run]);

  const [year, monthNumber] = month.split('-').map(Number);
  const first = new Date(Date.UTC(year, monthNumber - 1, 1));
  const days = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
  const entries: Entry[] = [];
  const undated: Opportunity[] = [];
  const matchingItems = (data?.items ?? []).filter(item => ids.includes(item.id) &&
    (!interests.length || interests.some(interest => matchesInterest(item, interest, fields))));
  for (const item of matchingItems) {
    const dates = calendarEntries(item);
    if (dates.length) entries.push(...dates);
    else undated.push(item);
  }
  const inMonth = entries.filter(e => e.start <= month + '-' + days && e.end >= month + '-01')
    .sort((a, b) => a.start.localeCompare(b.start) || a.item.title.localeCompare(b.item.title));
  const agenda = selected ? inMonth.filter(e => e.start <= selected && e.end >= selected) : inMonth;

  function navigate(next: string) {
    setMonth(next);
    setSelected('');
  }
  function shift(offset: number) {
    navigate(new Date(Date.UTC(year, monthNumber - 1 + offset, 1)).toISOString().slice(0, 7));
  }
  return <section className="calendar-panel" aria-label="북마크 일정 캘린더">
    <div className="calendar-interest-filter">
      <label>관심 분야 추가
        <select value="" onChange={event => setInterests([...interests, event.target.value])}>
          <option value="" disabled>{interests.length ? '관심 분야 더 선택' : '전체 관심 분야'}</option>
          {choices.map(choice => <option key={choice} value={choice} disabled={interests.includes(choice)}>{choice}</option>)}
        </select>
      </label>
      <div className="section-switch" role="group" aria-label="선택한 관심 분야">
        <button type="button" className="secondary" aria-pressed={!interests.length} onClick={() => setInterests([])}>전체</button>
        {interests.map(interest => <button type="button" key={interest} className="secondary"
          aria-label={interest + ' 선택 해제'} onClick={() => setInterests(interests.filter(value => value !== interest))}>
          {interest} ×</button>)}
      </div>
    </div>
    {interests.length > 0 && data && !loading && <p role="status">선택한 분야와 관련된 북마크 {matchingItems.length}건</p>}
    <div className="calendar-toolbar">
      <h2 aria-live="polite">{year}년 {monthNumber}월</h2>
      <div><button type="button" className="secondary" onClick={() => shift(-1)}>이전 달</button>
        <button type="button" className="secondary" onClick={() => navigate(today.slice(0, 7))}>이번 달</button>
        <button type="button" className="secondary" onClick={() => shift(1)}>다음 달</button></div>
    </div>
    {!ids.length && <p role="status">아직 저장한 공고가 없어요. 추천이나 공고 탐색에서 별표를 눌러 일정을 추가하세요.</p>}
    {ids.length > 0 && !available && <p role="status">공고 조회 기능이 준비되면 저장한 일정을 확인할 수 있어요.</p>}
    {loading && <p role="status">저장한 일정을 불러오는 중…</p>}
    {(error || data?.missing.some(id => ids.includes(id))) && <p role="alert">일부 저장한 공고를 불러오지 못했어요. <button
      type="button" className="secondary" onClick={() => setRetry(value => value + 1)}>다시 시도</button></p>}
    <div className="calendar-grid">
      {weekdays.map(day => <div className="calendar-weekday" key={day}>{day}</div>)}
      {Array.from({length: first.getUTCDay()}, (_, i) => <span aria-hidden="true" key={'blank-' + i} />)}
      {Array.from({length: days}, (_, i) => {
        const day = month + '-' + String(i + 1).padStart(2, '0');
        const events = inMonth.filter(e => e.start <= day && e.end >= day);
        return <button type="button" key={day} className="calendar-day" aria-label={day + ' 일정 ' + events.length + '건'}
          aria-current={day === today ? 'date' : undefined} aria-pressed={selected === day}
          onClick={() => setSelected(selected === day ? '' : day)}>
          <span className="calendar-number">{i + 1}</span>
          {events.slice(0, 2).map((e, index) => <span key={index} className="calendar-event">{e.label} · {e.item.title}</span>)}
          {events.length > 2 && <small>+{events.length - 2}</small>}
        </button>;
      })}
    </div>
    <div className="calendar-toolbar"><h3>{selected || monthNumber + '월'} 일정</h3>
      {selected && <button type="button" className="secondary" onClick={() => setSelected('')}>월 전체 보기</button>}
    </div>
    {agenda.length === 0 && !loading && available && ids.length > 0 && <p>이 기간에 표시할 일정이 없어요.</p>}
    {agenda.map((e, index) => <article className="calendar-entry" key={e.item.id + ':' + index}>
      <p className="calendar-date">{e.start}{e.end !== e.start && ' ~ ' + e.end} · {e.label}</p>
      <h4>{e.item.title}</h4><OpportunityDetails opportunity={e.item} />
    </article>)}
    {undated.length > 0 && <section><h3>날짜 미정</h3>
      {undated.map(item => <article className="calendar-entry" key={item.id}>
        <h4>{item.title}</h4><OpportunityDetails opportunity={item} />
      </article>)}
    </section>}
  </section>;
}
