import test from 'node:test';
import assert from 'node:assert/strict';
import {
  isCaseId, isScopeAnswer, isScopePayload, firstUnresolvedQuestion, nextScopeAnswers,
} from '../src/lib/case-scope.js';

test('scope input accepts only five known synthetic answers', () => {
  assert.equal(isScopeAnswer('yes'), true);
  assert.equal(isScopeAnswer('no'), true);
  assert.equal(isScopeAnswer('unsure'), true);
  assert.equal(isScopeAnswer('maybe'), false);
  for (const invalid of [null, [], {}, { answers: [] }, { answers: ['maybe'] },
    { answers: ['yes', 'no', 'yes', 'no', 'yes', 'no'] },
    { answers: ['yes'], address: 'Never accept private data' },
    { answers: 'yes' }]) {
    assert.equal(isScopePayload(invalid), false, JSON.stringify(invalid));
  }
  assert.equal(isScopePayload({ answers: ['yes'] }), true);
  assert.equal(isScopePayload({ answers: ['yes', 'yes', 'yes', 'no', 'yes'] }), true);
});

test('only UUID-shaped case IDs are routed to FastAPI', () => {
  assert.equal(isCaseId('a2345678-b234-c234-d234-e23456789012'), true);
  for (const invalid of ['', 'undefined', 'abc/../admin', '%2F', '12345',
    'a2345678-b234-c234-d234-e23456789012/other']) {
    assert.equal(isCaseId(invalid), false, invalid);
  }
});

test('new answers append and changing earlier answers removes later decisions', () => {
  assert.deepEqual(nextScopeAnswers([], 0, 'yes'), ['yes']);
  assert.deepEqual(nextScopeAnswers(['yes'], 1, 'yes'), ['yes', 'yes']);
  const complete = ['yes', 'yes', 'yes', 'no', 'yes'];
  assert.deepEqual(nextScopeAnswers(complete, 1, 'no'), ['yes', 'no']);
  assert.deepEqual(nextScopeAnswers(complete, 1, 'yes'), complete);
  assert.throws(() => nextScopeAnswers([], 3, 'yes'));
  assert.throws(() => nextScopeAnswers(['yes'], 1, 'invalid'));
});

test('resuming selects the first unknown or paused question', () => {
  assert.equal(firstUnresolvedQuestion([]), 0);
  assert.equal(firstUnresolvedQuestion(['yes', 'yes']), 2);
  assert.equal(firstUnresolvedQuestion(['yes', 'no']), 1);
  assert.equal(firstUnresolvedQuestion(['unsure']), 0);
  assert.equal(firstUnresolvedQuestion(['yes', 'yes', 'yes', 'no', 'yes']), 4);
});
