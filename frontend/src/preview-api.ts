import type { Capabilities, GuidanceResponse, Opportunity, Options, RecommendationRequest, RecommendationResponse } from './api';
import type { components } from './generated/api';

const date = (offset: number) => new Date(Date.now() + offset * 86_400_000).toISOString().slice(0, 10);
const checkedAt = new Date().toISOString();
const application: Opportunity['application'] = {status: 'open', opens_on: date(-3), closes_on: date(14)};
const source = {source_kind: 'synthetic', source_ids: ['preview-source'], checked_at: checkedAt} as const;

function opportunity(data: Pick<Opportunity, 'id' | 'type' | 'title' | 'organization' | 'summary'> & Partial<Opportunity>): Opportunity {
  return {
    ...source, source_ids: [...source.source_ids], source_url: 'https://example.org/',
    work_mode: 'unknown', requirements_coverage: 'partial', published_on: date(-3), application,
    ...data,
  };
}

const opportunities = [
  opportunity({id: 'preview-intern', type: 'job', subtype: 'internship', title: '프론트엔드 개발 인턴',
    organization: '예시 스튜디오', summary: '사용자 화면을 만들고 개발팀의 코드 리뷰에 참여하는 인턴십입니다.',
    requirements: ['개인 또는 팀 프로젝트 포트폴리오 제출', 'TOEIC 750점 이상 우대']}),
  opportunity({id: 'preview-cert', type: 'certification', title: '정보처리기사 시험 안내',
    organization: '예시 시험기관', summary: '소프트웨어 개발과 정보처리 관련 지식을 확인하는 시험 안내 카드입니다.',
    application: undefined,
    certification: {issuer: '예시 시험기관', status: 'active', exam_sessions: [
      {id: 'preview-session', name: '예시 시험 회차', exam_on: date(21), application,
        source_url: 'https://example.org/', checked_at: checkedAt},
    ]}}),
  opportunity({id: 'preview-contest', type: 'competition', title: '청년 웹 서비스 해커톤',
    organization: '예시 개발 커뮤니티', summary: '팀을 꾸려 웹 서비스를 만들고 결과를 발표하는 대회입니다.'}),
  opportunity({id: 'preview-job', type: 'job', title: '신입 웹 개발자 채용',
    organization: '예시 테크', summary: '서비스 화면과 공통 UI를 개발하는 신입 채용 카드입니다.',
    requirements: ['팀 프로젝트 경험 우대', 'SQLD 자격증 우대']}),
  opportunity({id: 'preview-notice', type: 'notice', title: '재학생 취업지원 프로그램 모집',
    organization: '예시대학교 취업지원센터', summary: '재학생 대상 이력서 점검과 모의 면접 프로그램 안내입니다.'}),
  opportunity({id: 'preview-event', type: 'event', subtype: 'job_fair', title: '청년 디지털 직무 채용 박람회',
    organization: '예시 청년센터', summary: '참여 기업의 직무 소개와 상담 부스를 둘러볼 수 있습니다.',
    event_schedule: {starts_on: date(17), ends_on: date(18)}}),
  opportunity({id: 'preview-research', type: 'project', title: '소프트웨어 연구실 학부연구생 모집',
    organization: '예시대학교 소프트웨어 연구실', summary: '웹 사용성 실험과 결과 정리를 함께하는 학부 연구 활동입니다.',
    requirements: ['프로젝트 경험 우대']}),
  opportunity({id: 'preview-graduate', type: 'event', subtype: 'briefing', title: '소프트웨어 대학원 입학 설명회',
    organization: '예시대학교 대학원', summary: '연구실별 연구 주제와 지원 일정을 소개합니다.',
    event_schedule: {starts_on: date(16)}}),
];

const catalogue = [
  ...opportunities,
  opportunity({
    id: 'preview-samsung-search', type: 'job', subtype: 'internship',
    title: '프론트엔드 인턴 모집 (검색 예시)',
    organization: '삼성 검색 예시',
    summary: '회사 이름으로 공고를 찾는 동작을 확인하기 위한 가상 인턴 공고입니다.',
    requirements: ['포트폴리오 제출 (예시)'],
  }),
];

const resources: components['schemas']['ResourceLink'][] = [
  {id: 'preview-resource', ...source, source_ids: [...source.source_ids], kind: 'official_site',
    name: '예시대학교 취업지원센터', url: 'https://example.org/', description: '공식 사이트 정보가 카드에 표시되는 방식의 예시입니다.'},
];

const options: Options = {
  status: 'draft',
  opportunity_types: ['job', 'certification', 'contest', 'competition', 'event', 'training', 'project', 'notice'],
  education_statuses: ['unknown', 'enrolled', 'leave', 'graduating', 'graduated', 'other'],
  experience_statuses: ['none', 'provided', 'unknown'],
  fields: [
    {code: 'software', label: '소프트웨어', aliases: ['소프트웨어', '개발', '프로그래밍']},
    {code: 'design', label: '디자인', aliases: ['디자인']},
    {code: 'business', label: '경영·사업', aliases: ['경영', '사업']},
    {code: 'data', label: '데이터', aliases: ['데이터', '데이터 분석']},
  ],
};

const capabilities: Capabilities = Object.fromEntries(
  ['recommendations', 'opportunities', 'resource-links', 'career-roles', 'activity-plan', 'interview-guide']
    .map(feature => [feature, {enabled: true, implemented: true}]),
);

const recommendations: RecommendationResponse = {
  engine: 'rules',
  candidate_count: opportunities.length,
  items: opportunities.map((item, index) => ({
    opportunity: item,
    recommendation: {
      opportunity_id: item.id, relevance_score: 90 - index * 3, eligibility: 'unknown', explanation_source: 'template',
      reasons: [{text: '입력 후 추천 이유가 표시되는 위치를 확인할 수 있는 고정 예시입니다.', evidence_ids: []}],
      cautions: ['이 카드의 기관, 일정, 기준은 화면 확인용 예시입니다.'],
    },
  })),
};

const roles: GuidanceResponse<'career-roles'> = {
  items: [{role_id: 'preview-frontend', explanation: '프론트엔드 개발자는 사용자 화면을 구현하고 서비스 API를 연결해요.', source_ids: []}],
};

const plan: GuidanceResponse<'activity-plan'> = {
  steps: [
    {kind: 'general_preparation', title: '해커톤 경험을 포트폴리오에 정리하기', description: '맡은 역할과 해결한 문제, 직접 만든 화면을 정리해 보세요.'},
    {kind: 'opportunity', title: '학부연구생 모집 상세 확인하기', description: '연구 주제와 활동 기간을 확인해 보세요.', opportunity_id: 'preview-research'},
  ],
};

export function previewResponse(path: string, init: RequestInit): Response {
  const url = new URL(path, 'http://localhost');
  switch (url.pathname) {
    case '/health': return Response.json({status: 'ok', contract_version: '4.1-draft'});
    case '/options': return Response.json(options);
    case '/capabilities': return Response.json(capabilities);
    case '/recommendations': return Response.json(recommendations);
    case '/career-roles': return Response.json(roles);
    case '/activity-plan': return Response.json(plan);
    case '/interview-guide': {
      const body = typeof init.body === 'string' ? JSON.parse(init.body) as RecommendationRequest : undefined;
      const experienceId = body?.profile.experiences?.[0]?.id;
      const data: GuidanceResponse<'interview-guide'> = {questions: [{
        kind: 'practice', question: '팀 프로젝트에서 맡은 역할과 해결한 문제를 설명해 주세요.',
        preparation_tip: '상황, 직접 한 일, 결과를 순서대로 말해 보세요.',
        experience_ids: experienceId ? [experienceId] : [],
      }]};
      return Response.json(data);
    }
    case '/opportunities':
    case '/resource-links': {
      const words = (url.searchParams.get('q') ?? '').trim().toLowerCase().split(/\s+/).filter(Boolean);
      const types = url.searchParams.getAll('types');
      const list = url.pathname === '/opportunities' ? catalogue.filter(item => {
        if (types.length && !types.includes(item.type)) return false;
        const text = [item.title, item.organization, item.summary, ...(item.tags ?? [])].join(' ').toLowerCase();
        return words.every(word => text.includes(word));
      }).sort((a, b) => a.id.localeCompare(b.id)) : resources;
      const offset = Number(url.searchParams.get('offset') ?? 0);
      const limit = Number(url.searchParams.get('limit') ?? 20);
      return Response.json({items: list.slice(offset, offset + limit), total: list.length, offset, limit});
    }
    default: {
      const item = catalogue.find(entry => url.pathname === `/opportunities/${entry.id}`);
      return item ? Response.json(item) : new Response(null, {status: 404});
    }
  }
}
