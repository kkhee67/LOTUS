import assert from 'node:assert/strict';
import test from 'node:test';
import {appendPage} from '../src/features/opportunities/pagination.ts';

test('overlapping pages preserve order, update duplicate IDs and keep inputs unchanged', () => {
  const previous = {items: [{id: 'a', title: 'old'}, {id: 'b', title: 'before'}], total: 3, next: 2};
  const page = {items: [{id: 'b', title: 'after'}, {id: 'c', title: 'new'}], total: 3, offset: 2, limit: 20};
  const original = structuredClone({previous, page});
  assert.deepEqual(appendPage(previous, page), {
    items: [{id: 'a', title: 'old'}, {id: 'b', title: 'after'}, {id: 'c', title: 'new'}], total: 3, next: 4,
  });
  assert.deepEqual({previous, page}, original);
});

test('a final empty page terminates pagination, including an initially empty catalog', () => {
  assert.deepEqual(appendPage(undefined, {items: [], total: 0, offset: 0, limit: 20}), {items: [], total: 0, next: 20});
  const previous = {items: [{id: 'a'}], total: 1, next: 1};
  const result = appendPage(previous, {items: [], total: 1, offset: 1, limit: 20});
  assert.equal(result.next >= result.total, true);
  assert.deepEqual(result.items, previous.items);
});
