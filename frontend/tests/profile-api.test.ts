import assert from 'node:assert/strict';
import test from 'node:test';
import {ApiError, getApi, getGuidance, getList, getOpportunity, recommend, type RecommendationRequest} from '../src/api.ts';

const body: RecommendationRequest = {
  profile: {goal: '포트폴리오', education_status: 'unknown', experience_status: 'unknown'},
  allow_external_ai: false,
  limit: 8,
};
const ready = {enabled: true, implemented: true};
const signal = new AbortController().signal;

test('recommendations require both capability flags before any network request', async context => {
  const fetch = context.mock.method(globalThis, 'fetch');
  for (const capability of [undefined, {enabled: false, implemented: true}, {enabled: true, implemented: false}]) {
    await assert.rejects(recommend(capability, body, signal), {kind: 'unavailable'});
  }
  assert.equal(fetch.mock.callCount(), 0);
});

test('enabled recommendations send a JSON body and never put profile data in the URL', async context => {
  const fetch = context.mock.method(globalThis, 'fetch', async () =>
    Response.json({items: [], candidate_count: 0, engine: 'rules'}));
  const result = await recommend(ready, body, signal);
  assert.deepEqual(result.items, []);
  assert.deepEqual(fetch.mock.calls[0].arguments, [
    'http://localhost:8000/api/v1/recommendations',
    {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), signal},
  ]);
});

test('options and recommendations distinguish HTTP and network failures', async context => {
  const fetch = context.mock.method(globalThis, 'fetch', async () => new Response(null, {status: 500}));
  await assert.rejects(getApi('/options', signal), {kind: 'server'});
  for (const [status, kind] of [[422, 'validation'], [503, 'unavailable'], [500, 'server']] as const) {
    fetch.mock.mockImplementation(async () => new Response(null, {status}));
    await assert.rejects(recommend(ready, body, signal), {kind});
  }
  fetch.mock.mockImplementation(async () => {throw new TypeError('network');});
  await assert.rejects(getApi('/options', signal), {kind: 'network'});
  await assert.rejects(recommend(ready, body, signal), ApiError);
});

test('catalogue, saved detail and career tools never call disabled APIs', async context => {
  const fetch = context.mock.method(globalThis, 'fetch');
  const disabled = {enabled: true, implemented: false};
  await assert.rejects(getList('opportunities', disabled, 0, signal), {kind: 'unavailable'});
  await assert.rejects(getList('resource-links', disabled, 0, signal), {kind: 'unavailable'});
  await assert.rejects(getOpportunity('job:123', disabled, signal), {kind: 'unavailable'});
  await assert.rejects(getGuidance('career-roles', disabled, {profile: body.profile, allow_external_ai: false, limit: 5}, signal), {kind: 'unavailable'});
  assert.equal(fetch.mock.callCount(), 0);
});

test('catalogue requests use pagination and saved details handle missing records', async context => {
  const fetch = context.mock.method(globalThis, 'fetch', async () =>
    Response.json({items: [], total: 20, offset: 20, limit: 20}));
  await getList('resource-links', ready, 20, signal);
  assert.equal(fetch.mock.calls[0].arguments[0], 'http://localhost:8000/api/v1/resource-links?limit=20&offset=20');
  fetch.mock.mockImplementation(async () => new Response(null, {status: 404}));
  await assert.rejects(getOpportunity('job:123', ready, signal), {kind: 'not-found'});
  assert.equal(fetch.mock.calls[1].arguments[0], 'http://localhost:8000/api/v1/opportunities/job%3A123');
});
