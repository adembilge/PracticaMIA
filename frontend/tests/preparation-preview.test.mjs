import assert from 'node:assert/strict';
import test from 'node:test';
import {
  preparationPreviewEnabled, isPreparationFactsPayload, isPreparationPayload,
  serializeReviewedPreparationPackage, serializeSyntheticAnprDraft, serializeSyntheticAnprText,
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



test('bounded guide questions permit only an English or Italian short question', () => {
  assert.equal(isPreparationPayload('guide', {
    question: 'What official sources exist?', language: 'en',
  }), true);
  assert.equal(isPreparationPayload('guide', {
    question: 'Qual è il prossimo passo?', language: 'it',
  }), true);
  for (const bad of [
    { question: 'x', language: 'en' },
    { question: 'Valid?', language: 'fr' },
    { question: 'x'.repeat(181), language: 'en' },
    { question: 'Valid?', language: 'en', approve: true },
    { question: ['not', 'a', 'string'], language: 'en' },
  ]) assert.equal(isPreparationPayload('guide', bad), false);
});

test('reviewed synthetic preparation export remains a non-submitted user-controlled artifact', () => {
  const digest = 'a'.repeat(64);
  const data = {
    case_id: '00000000-0000-4000-8000-000000000001',
    confirmed_facts: { property_address: 'Fictional Via 10 Milano' },
    government_submission: 'user_only_not_submitted',
  };
  const exported = JSON.parse(serializeReviewedPreparationPackage(data, digest));
  assert.equal(exported.simulation_only, true);
  assert.equal(exported.official_application_form, false);
  assert.equal(exported.government_submission_status, 'NOT_SUBMITTED');
  assert.equal(exported.review_digest, digest);
  assert.deepEqual(exported.package, data);
  assert.throws(() => serializeReviewedPreparationPackage(data, 'short'));
  assert.throws(() => serializeReviewedPreparationPackage(
    { ...data, government_submission: 'approved' }, digest));
  assert.throws(() => serializeReviewedPreparationPackage(null, digest));
});

test('ANPR worksheet export never claims an approved form or submission', () => {
  const demo = {
    artifact_type: 'synthetic_anpr_field_transcription_draft',
    simulation_only: true,
    official_form: false,
    government_submission_status: 'NOT_SUBMITTED',
    source_currentness_verified: false,
    state: 'field_transcription_complete',
    sections: [{ id: 'housing', fields: [{key:'rental_registration_number',value:'TEST-0001'}]}],
  };
  const data = JSON.parse(serializeSyntheticAnprDraft(demo));
  assert.equal(data.government_submission_status, 'NOT_SUBMITTED');
  assert.equal(data.official_form, false);
  assert.match(data.export_disclaimer, /not an official/i);
  assert.equal(data.sections[0].fields[0].value, 'TEST-0001');
  assert.throws(() => serializeSyntheticAnprDraft({...demo, official_form:true}));
  assert.throws(() => serializeSyntheticAnprDraft({...demo, simulation_only:false}));
  assert.throws(() => serializeSyntheticAnprDraft({...demo, government_submission_status:'SUBMITTED'}));
});

test('readable ANPR worksheet output is not a submission or official form', () => {
  const demo = {
    artifact_type: 'synthetic_anpr_field_transcription_draft',
    simulation_only: true,
    official_form: false,
    government_submission_status: 'NOT_SUBMITTED',
    source_currentness_verified: false,
    state: 'needs_field_information',
    sections: [{ id: 'housing', title_en: 'Registered rental', fields: [
      {key:'rental_registration_number',label_en:'Registration number',value:'TEST-0001',valid:true},
      {key:'rental_contract_date',label_en:'Contract date',value:'',valid:false},
    ]}],
  };
  const txt = serializeSyntheticAnprText(demo);
  assert.match(txt, /NOT SUBMITTED/);
  assert.match(txt, /NOT AN OFFICIAL APPLICATION/);
  assert.match(txt, /Registration number: TEST-0001/);
  assert.match(txt, /Contract date: \[not confirmed\]/);
  assert.throws(() => serializeSyntheticAnprText({ ...demo, official_form: true }));
});
