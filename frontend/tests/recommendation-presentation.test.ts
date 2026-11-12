import assert from 'node:assert/strict';
import test from 'node:test';
import {applicationStatus, closesToday, sourceHref} from '../src/features/recommendations/presentation.ts';
import {certificationRequirements, inCategory, languageRequirements, researchRequirements} from '../src/features/recommendations/categories.ts';

test('research and graduate school category includes opportunities and preserves degree requirements', () => {
  assert.equal(inCategory({type: 'notice', title: '인공지능 연구실 학부연구생 모집'}, 'research'), true);
  assert.equal(inCategory({type: 'event', title: '대학원 입학 설명회'}, 'research'), true);
  assert.equal(inCategory({type: 'training', tags: ['대학원']}, 'research'), true);
  const job = {type: 'job' as const, requirements: ['석사 학위 필수', '학부 연구 경험 우대', '포트폴리오 제출']};
  assert.equal(inCategory(job, 'research'), true);
  assert.deepEqual(researchRequirements(job), ['석사 학위 필수', '학부 연구 경험 우대']);
  assert.equal(inCategory({type: 'job', title: '웹 개발자 채용', requirements: ['포트폴리오 제출']}, 'research'), false);
});

test('recommendation categories distinguish internship, employer hiring and preparation opportunities', () => {
  assert.equal(inCategory({type: 'job', subtype: 'internship'}, 'internships'), true);
  assert.equal(inCategory({type: 'job', subtype: 'internship'}, 'jobs'), false);
  assert.equal(inCategory({type: 'job'}, 'jobs'), true);
  for (const type of ['contest', 'competition', 'project', 'training'] as const) {
    assert.equal(inCategory({type}, 'portfolio'), true);
  }
  assert.equal(inCategory({type: 'certification'}, 'certifications'), true);
  assert.equal(inCategory({type: 'notice'}, 'notices'), true);
  assert.equal(inCategory({type: 'event'}, 'events'), true);
});

test('language requirements preserve the source wording and exclude unrelated requirements', () => {
  const opportunity = {type: 'job', requirements: ['포트폴리오 제출', 'TOEIC 750점 이상 우대', 'TOEIC 750점 이상 우대']} as const;
  const item = {...opportunity, requirements: [...opportunity.requirements]};
  assert.deepEqual(languageRequirements(item), ['TOEIC 750점 이상 우대']);
  assert.equal(inCategory(item, 'languages'), true);
  assert.equal(inCategory({type: 'job', requirements: ['포트폴리오 제출']}, 'languages'), false);
});

test('job cards can appear under certifications without turning preferred credentials into requirements', () => {
  const opportunity = {type: 'job' as const, requirements: ['SQLD 자격증 우대', '포트폴리오 제출']};
  assert.deepEqual(certificationRequirements(opportunity), ['SQLD 자격증 우대']);
  assert.equal(inCategory(opportunity, 'certifications'), true);
  assert.equal(inCategory(opportunity, 'jobs'), true);
});

test('unknown stays unknown around the start and closes after the Seoul date', () => {
  const application = {status: 'unknown', opens_on: '2026-11-12', closes_on: '2026-11-12'} as const;
  const before = new Date('2026-11-11T14:59:59Z');
  const on = new Date('2026-11-12T14:59:59Z');
  const after = new Date('2026-11-12T15:00:00Z');
  assert.equal(applicationStatus(application, before), 'unknown');
  assert.equal(applicationStatus(application, on), 'unknown');
  assert.equal(closesToday(application, on), true);
  assert.equal(applicationStatus(application, after), 'closed');
  assert.equal(closesToday(application, after), false);
});

test('status changes at exact start and end instants, preserving an explicit closure', () => {
  const application = {status: 'upcoming', opens_at: '2026-11-12T12:00:00+09:00', closes_at: '2026-11-12T13:00:00+09:00'} as const;
  const before = new Date('2026-11-12T02:59:59Z');
  assert.equal(applicationStatus(application, before), 'upcoming');
  assert.equal(applicationStatus(application, new Date('2026-11-12T03:00:00Z')), 'open');
  assert.equal(applicationStatus(application, new Date('2026-11-12T04:00:00Z')), 'closed');
  assert.equal(applicationStatus({...application, status: 'closed'}, before), 'closed');
});

test('source links must be absolute HTTP(S) URLs without credentials', () => {
  assert.equal(sourceHref('https://example.org/jobs/1'), 'https://example.org/jobs/1');
  assert.equal(sourceHref('http://example.org/jobs/1'), 'http://example.org/jobs/1');
  for (const url of ['javascript:alert(1)', 'data:text/plain,abc', '//example.org', '/relative', 'https://user:pass@example.org']) {
    assert.equal(sourceHref(url), undefined);
  }
});
