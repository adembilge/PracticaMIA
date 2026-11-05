import test from 'node:test';
import assert from 'node:assert/strict';
import {
  reviewerPreviewEnabled, isBrowserReviewBatchPayload,
} from '../src/lib/reviewer-preview.js';

const a = {
  source_id: 'milano-residence-faq',
  version_id: '123e4567-e89b-12d3-a456-426614174000',
  expected_sha256: 'a'.repeat(64),
};
const b = {
  source_id: 'milano-foreign-rental-documents',
  version_id: '123e4567-e89b-12d3-a456-426614174001',
  expected_sha256: 'b'.repeat(64),
};
const good = {
  items: [a, b],
  review_note: 'Reviewed each official page, applicability, and capture provenance.',
  confirmed_source_review: true,
};

test('reviewer interface is explicitly enabled only outside production', () => {
  assert.equal(reviewerPreviewEnabled({}), false);
  assert.equal(reviewerPreviewEnabled({
    ENABLE_REVIEW_UI: '1', VERCEL_ENV: 'production', NODE_ENV: 'production',
  }), false);
  assert.equal(reviewerPreviewEnabled({
    ENABLE_REVIEW_UI: '1', VERCEL_ENV: 'preview', NODE_ENV: 'production',
  }), true);
  assert.equal(reviewerPreviewEnabled({
    ENABLE_REVIEW_UI: '1', NODE_ENV: 'development',
  }), true);
  assert.equal(reviewerPreviewEnabled({
    ENABLE_REVIEW_UI: 'true', VERCEL_ENV: 'preview',
  }), false);
});

test('review API payload rejects forged status, reviewer and duplicate hashes', () => {
  assert.equal(isBrowserReviewBatchPayload(good), true);
  for (const invalid of [
    null, [], {}, { ...good, actor_subject: 'other-user' },
    { ...good, confirmed_source_review: false },
    { ...good, review_note: 'approve' },
    { ...good, review_note: 'x'.repeat(451) },
    { ...good, items: [] },
    { ...good, items: [a, a] },
    { ...good, items: [a, { ...a, source_id: 'different-source' }] },
    { ...good, items: [a, { ...b, version_id: a.version_id }] },
    { ...good, items: [a, { ...b, expected_sha256: 'X'.repeat(64) }] },
    { ...good, items: [{ ...a, status: 'approved' }] },
    { ...good, items: Array(16).fill(a) },
  ]) {
    assert.equal(isBrowserReviewBatchPayload(invalid), false);
  }
});
