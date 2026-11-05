import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DEMO_ANSWERS, classifyScope, validateIntake,
} from '../src/lib/flow.js';
import { isScopePayload } from '../src/lib/case-scope.js';
import {
  sameOrigin, backendOrigin,
} from '../src/lib/auth-configuration.js';
import {
  isBrowserReviewBatchPayload,
} from '../src/lib/reviewer-preview.js';

test('all 243 five-step demo states agree with an independent finite-state oracle', () => {
  const answers = ['yes', 'no', 'unsure'];
  let total = 0;
  for (let n = 0; n < 243; n++) {
    let index = n;
    const inputs = Array.from({ length: 5 }, () => {
      const value = answers[index % 3]; index = Math.floor(index / 3);
      return value;
    });
    let expected = 'provisionally_in_scope';
    for (let j = 0; j < 5; j++) {
      if (inputs[j] === 'unsure') {
        expected = 'needs_information';
        break;
      }
      if (inputs[j] !== DEMO_ANSWERS[j]) {
        expected = 'unsupported';
        break;
      }
    }
    assert.equal(classifyScope(inputs), expected);
    assert.equal(isScopePayload({ answers: inputs }), true);
    total++;
  }
  assert.equal(total, 243);
});

test('real calendar boundaries and invalid over-posting never silently pass', () => {
  for (const date of ['2026-02-29', '2025-02-29', '2026-13-01',
    '2026-00-12', '2026-11-31', '2026-01-00', '2026-12-32',
    'n/a', '2026-11-06T00:00:00', '<script>', '2026-1-6']) {
    assert.equal(
      validateIntake({ previousAddress: 'A', newAddress: 'B', movedOn: date }).movedOn,
      'invalid', date,
    );
  }
  assert.equal(
    validateIntake({ previousAddress: 'A', newAddress: 'B', movedOn: '2024-02-29' }).movedOn,
    undefined,
  );
  for (const bad of [
    { answers: ['yes'], status: 'officially_confirmed' },
    { answers: ['yes'], owner_subject: 'attacker' },
    { answers: ['yes'], approved: true },
    { answers: ['yes', 'yes', 'yes', 'no', 'yes', 'yes'] },
    { answers: [true] }, { answers: ['YES'] },
    { answers: '__proto__' },
  ]) assert.equal(isScopePayload(bad), false);
});

test('CSRF origin and backend URL controls reject parser confusion and credentials', () => {
  const target = 'https://practicamia.vercel.app/api/cases';
  const validOrigin = 'https://practicamia.vercel.app';
  assert.equal(sameOrigin(target, validOrigin), true);
  for (const supplied of [
    '', 'null', 'http://practicamia.vercel.app',
    'https://practicamia.vercel.app.evil.test',
    'https://evil.test@practicamia.vercel.app',
    'https://practicamia.vercel.app@evil.test',
    'https://practicamia.vercel.app/path',
    'https://practicamia.vercel.app?fake=1',
    'data:text/html,hello', 'https://practicamia.vercel.app#fragment',
    'https://practicamia.vercel.app:444',
  ]) assert.equal(sameOrigin(target, supplied), false, supplied);
  for (const targetHost of [
    'https://user:pass@evil.test/',
    'http://backend.example.test',
    'javascript:alert(1)', 'https://backend.example.test/api',
    'https://backend.example.test/?secret=123',
    'https://backend.example.test/#fragment',
  ]) assert.equal(backendOrigin(targetHost), null, targetHost);
});

test('review API does not permit crafted role/status/duplicate ID injection', () => {
  const item = {
    source_id: 'milano-residence-faq',
    version_id: '123e4567-e89b-12d3-a456-426614174000',
    expected_sha256: 'a'.repeat(64),
  };
  const payload = {
    items: [item],
    review_note: 'Review of exact official text and current applicability.',
    confirmed_source_review: true,
  };
  assert.equal(isBrowserReviewBatchPayload(payload), true);
  for (const attack of [
    { ...payload, principal: { sub: 'victim' } },
    { ...payload, is_admin: true },
    { ...payload, items: [{ ...item, actor_subject: 'other-user' }] },
    { ...payload, items: [{ ...item, status: 'approved' }] },
    { ...payload, items: [item, { ...item, version_id: '123e4567-e89b-12d3-a456-426614174001' }] },
    { ...payload, items: [{ ...item, expected_sha256: 'A'.repeat(64) }] },
    { ...payload, confirmed_source_review: 1 },
    { ...payload, review_note: ''.padEnd(500, 'x') },
  ]) assert.equal(isBrowserReviewBatchPayload(attack), false);
});
