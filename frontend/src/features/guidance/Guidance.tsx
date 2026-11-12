import type {ReactNode} from 'react';
import {canRecommend, getGuidance, type Capabilities, type Capability, type GuidanceFeature, type GuidanceResponse, type Opportunity, type RecommendationRequest} from '../../api';
import {sourceHref} from '../recommendations/presentation';
import {TextList} from '../recommendations/RecommendationResults';
import {useApiTask} from '../useApiTask';

type Profile = RecommendationRequest['profile'];

function GuidanceSection<T extends GuidanceFeature>({feature, title, capability, profile, render}: {
  feature: T;
  title: string;
  capability?: Capability;
  profile?: Profile;
  render: (response: GuidanceResponse<T>) => ReactNode;
}) {
  const task = useApiTask<GuidanceResponse<T>>();
  const available = canRecommend(capability);
  return <section className="guidance-card" aria-labelledby={`${feature}-heading`}>
    <h3 id={`${feature}-heading`}>{title}</h3>
    {!available && <p className="availability">기능 준비 중이에요.</p>}
    {available && !profile && <p>기본 정보에서 입력을 먼저 확인해 주세요.</p>}
    {task.error && <p className="error" role="alert">{task.error}</p>}
    {task.data && <>
      {task.data.warnings?.length ? <TextList items={task.data.warnings} /> : null}
      {render(task.data)}
    </>}
    {available && profile && <button type="button" className="secondary" disabled={task.loading}
      onClick={() => void task.run(signal => getGuidance(feature, capability, {
        profile, allow_external_ai: false, ...(feature === 'career-roles' ? {limit: 5} : {}),
      }, signal))}>
      {task.loading ? '불러오는 중…' : task.error ? '다시 시도' : task.data ? '다시 보기' : `${title} 보기`}
    </button>}
  </section>;
}

export function Guidance({capabilities, profile, opportunities}: {
  capabilities?: Capabilities;
  profile?: Profile;
  opportunities?: Opportunity[];
}) {
  const byId = new Map(opportunities?.filter(item => item.source_kind === 'real').map(item => [item.id, item]));
  const activities = new Map(profile?.experiences?.map(experience => [experience.id, experience.title]));
  return <section id="guidance" className="feature-panel" aria-label="진로 준비 도구">
    <div className="guidance-grid">
      <GuidanceSection feature="career-roles" title="직무 설명" capability={capabilities?.['career-roles']} profile={profile}
        render={data => data.items.length ? <ul>{data.items.map(item =>
          <li key={item.role_id}>{item.explanation}</li>,
        )}</ul> : <p>추천된 직무 설명이 없어요.</p>} />
      <GuidanceSection feature="activity-plan" title="다음 활동" capability={capabilities?.['activity-plan']} profile={profile}
        render={data => data.steps.length ? <ul>{data.steps.map((step, index) => {
          const opportunity = step.opportunity_id ? byId.get(step.opportunity_id) : undefined;
          const href = opportunity && sourceHref(opportunity.source_url);
          return <li key={index}>
            <p className="result-meta">{step.kind === 'opportunity' ? '공고 연결 활동' : '일반 준비 활동'}</p>
            <strong>{step.title}</strong><p>{step.description}</p>
            {href && <a href={href} target="_blank" rel="noopener noreferrer">연결된 공고 원문 (새 탭)</a>}
          </li>;
        })}</ul> : <p>추천된 다음 활동이 없어요.</p>} />
      <GuidanceSection feature="interview-guide" title="면접 준비" capability={capabilities?.['interview-guide']} profile={profile}
        render={data => data.questions.length ? <ol>{data.questions.map((item, index) => {
          const titles = item.experience_ids?.map(id => activities.get(id)).filter(Boolean) ?? [];
          return <li key={index}>
            <p className="result-meta">연습용 질문</p>
            <strong>{item.question}</strong><p>{item.preparation_tip}</p>
            {titles.length > 0 && <p>참고할 내 경험 · {titles.join(', ')}</p>}
          </li>;
        })}</ol> : <p>확인할 면접 연습 질문이 없어요.</p>} />
    </div>
  </section>;
}
