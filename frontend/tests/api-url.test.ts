import assert from 'node:assert/strict';
import test from 'node:test';
import { apiBase } from '../src/api-url.ts';

test('server-only URL produces exactly one API prefix', () => {
  assert.equal(apiBase(undefined), 'http://localhost:8000/api/v1');
  assert.equal(apiBase('http://localhost:8000/'), 'http://localhost:8000/api/v1');
});
test('reject duplicated prefix, credentials, query, and invalid scheme', () => {
  for (const value of ['http://localhost:8000/api/v1', 'https://user:pass@example.org',
    'https://example.org?token=x', 'file:///tmp/test']) {
    assert.throws(() => apiBase(value));
  }
});
