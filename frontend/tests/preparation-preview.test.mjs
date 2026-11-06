import assert from 'node:assert/strict';
import test from 'node:test';
import {
  preparationPreviewEnabled, isPreparationFactsPayload, isPreparationPayload,
} from '../src/lib/preparation-preview.js';

test('isolated UI is never enabled in Vercel production', () => {
  assert.equal(preparationPreviewEnabled({ VERCEL_ENV: 'production', ENABLE_PREPARATION_UI: '1' }), false);
  assert.equal(preparationPreviewEnabled({ VERCEL_ENV: 'preview', ENABLE_PREPARATION_UI: '1' }), true);
  assert.equal(preparationPreviewEnabled({ VERCEL_ENV: 'preview', ENABLE_PREPARATION_UI: '0' }), false);
  assert.equal(preparationPreviewEnabled({ VERCEL_ENV: 'production', ENABLE_PREPARATION_UI: 'yes' }), false);
});

test('facts permit only bounded flat scalar confirmed values', () => {
  assert.equal(isPreparationFactsPayload({ confirmed_facts: {
    synthetic_eligibility: 'yes', housing_arrangement: 'fictional_rental',
  }}), true);
  for (const data of [
    {}, { confirmed_facts: null }, { confirmed_facts: [] },
    { confirmed_facts: { '__proto__.admin': true } },
    { confirmed_facts: { fact: { nested: 'unsafe' } } },
    { confirmed_facts: { address: 'x'.repeat(241) } },
    { confirmed_facts: { age: Number.MAX_SAFE_INTEGER + 10 } },
  ]) assert.equal(isPreparationFactsPayload(data), false);
});

test('document and package review payloads reject extra keys', () => {
  assert.equal(isPreparationPayload('document/review', { confirm_document: true }), true);
  assert.equal(isPreparationPayload('document/review', { confirm_document: true, admin: true }), false);
  assert.equal(isPreparationPayload('package/approve', { review_digest: 'a'.repeat(64) }), true);
  assert.equal(isPreparationPayload('package/approve', { review_digest: 'a'.repeat(63) }), false);
  assert.equal(isPreparationPayload('document/confirm-fields', {
    field_name: 'property_address', raw_value: 'Synthetic Via 10',
    confirmed_value: 'Synthetic Via 10', page: 1,
  }), true);
  assert.equal(isPreparationPayload('document/confirm-fields', {
    field_name: 'owner_subject', raw_value: 'x', confirmed_value: 'y', page: 1,
  }), false);
});
