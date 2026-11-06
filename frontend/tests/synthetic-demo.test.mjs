import assert from 'node:assert/strict';
import test from 'node:test';
import {
  DEMO_DISCLAIMER, FICTIONAL_ADDRESS, OTHER_FICTIONAL_ADDRESS,
  SYNTHETIC_EVIDENCE, createSyntheticCase, updateSyntheticFacts,
  confirmSyntheticFacts, loadSyntheticDocument, confirmSyntheticDocumentField,
  reviewSyntheticDocument, evaluateSyntheticCase, buildSyntheticPackage,
  approveSyntheticPackage, syntheticDocumentText,
} from '../src/lib/synthetic-demo.js';
import { syntheticDemoAvailable } from '../src/lib/synthetic-demo-guard.js';

function confirmedStandard() {
  return confirmSyntheticFacts(createSyntheticCase('standard'));
}

function readyStandard() {
  let state = confirmedStandard();
  state = loadSyntheticDocument(state);
  state = confirmSyntheticDocumentField(state, FICTIONAL_ADDRESS);
  return reviewSyntheticDocument(state);
}

test('synthetic-only route is never available on production deployment', () => {
  assert.equal(syntheticDemoAvailable({ VERCEL_ENV: 'production', NODE_ENV: 'production' }), false);
  assert.equal(syntheticDemoAvailable({ VERCEL_ENV: 'production', NODE_ENV: 'development' }), false);
  assert.equal(syntheticDemoAvailable({ VERCEL_ENV: 'preview', NODE_ENV: 'production' }), true);
  assert.equal(syntheticDemoAvailable({ NODE_ENV: 'development' }), true);
  assert.equal(syntheticDemoAvailable({ NODE_ENV: 'production' }), false);
});

test('safe happy path blocks progression until facts and document are explicitly reviewed', () => {
  let state = createSyntheticCase();
  assert.equal(evaluateSyntheticCase(state).status, 'needs_confirmation');
  assert.equal(buildSyntheticPackage(state), null);
  state = confirmSyntheticFacts(state);
  assert.equal(evaluateSyntheticCase(state).status, 'needs_documents');
  assert.equal(buildSyntheticPackage(state), null);
  state = loadSyntheticDocument(state);
  assert.equal(evaluateSyntheticCase(state).status, 'needs_field_confirmation');
  assert.match(syntheticDocumentText(state), /FICTIONAL SAMPLE DOCUMENT/);
  assert.match(syntheticDocumentText(state), /Property address/);
  state = confirmSyntheticDocumentField(state, FICTIONAL_ADDRESS);
  assert.equal(evaluateSyntheticCase(state).status, 'needs_document_review');
  assert.equal(buildSyntheticPackage(state), null);
  state = reviewSyntheticDocument(state);
  assert.equal(evaluateSyntheticCase(state).status, 'reviewable');
  const packageData = buildSyntheticPackage(state);
  assert.ok(packageData);
  assert.equal(packageData.government_submission_status, 'NOT_SUBMITTED');
  assert.equal(packageData.simulation_only, true);
  assert.equal(packageData.documents[0].extraction_method, 'simulated_fixture_not_ocr');
  assert.equal(packageData.checklist[0].official_requirement, false);
  assert.equal(packageData.evidence[0].official, false);
  assert.match(packageData.disclaimer, /FICTIONAL SIMULATION/);
  state = approveSyntheticPackage(state);
  assert.equal(evaluateSyntheticCase(state).status, 'simulated_handoff');
  assert.equal(buildSyntheticPackage(state).government_submission_status, 'NOT_SUBMITTED');
});

test('missing information requires targeted answer instead of guessing eligibility', () => {
  let state = confirmSyntheticFacts(createSyntheticCase('missing'));
  let assessed = evaluateSyntheticCase(state);
  assert.equal(assessed.status, 'needs_information');
  assert.deepEqual(assessed.missing_fields, ['previous_registration_context']);
  assert.equal(assessed.checklist.length, 0);
  assert.equal(buildSyntheticPackage(state), null);
  state = updateSyntheticFacts(state, { previous_registration_context: 'in_milan_example' });
  assert.equal(evaluateSyntheticCase(state).status, 'needs_confirmation');
  assert.equal(evaluateSyntheticCase(confirmSyntheticFacts(state)).status, 'needs_documents');
});

test('unsupported simulated route never returns a checklist or package', () => {
  let state = confirmSyntheticFacts(createSyntheticCase('unsupported'));
  const result = evaluateSyntheticCase(state);
  assert.equal(result.decision, 'unsupported');
  assert.equal(result.checklist.length, 0);
  assert.equal(result.evidence.length, 0);
  assert.equal(buildSyntheticPackage(state), null);
  assert.throws(() => approveSyntheticPackage(state), /Cannot approve/);

  state = updateSyntheticFacts(state, {
    previous_registration_context: 'in_milan_example',
    household_context: 'joining_household_example',
  });
  assert.equal(evaluateSyntheticCase(confirmSyntheticFacts(state)).status, 'unsupported');
});

test('document/address conflict blocks package until explicit correction and re-review', () => {
  let state = confirmSyntheticFacts(createSyntheticCase('conflict'));
  state = loadSyntheticDocument(state);
  assert.equal(state.extraction_value, OTHER_FICTIONAL_ADDRESS);
  state = confirmSyntheticDocumentField(state, OTHER_FICTIONAL_ADDRESS);
  state = reviewSyntheticDocument(state);
  assert.equal(evaluateSyntheticCase(state).status, 'needs_review');
  assert.equal(buildSyntheticPackage(state), null);
  assert.throws(() => approveSyntheticPackage(state), /Cannot approve/);
  state = confirmSyntheticDocumentField(state, FICTIONAL_ADDRESS);
  assert.equal(evaluateSyntheticCase(state).status, 'needs_document_review');
  state = reviewSyntheticDocument(state);
  assert.equal(evaluateSyntheticCase(state).status, 'reviewable');
  assert.equal(buildSyntheticPackage(state).documents[0].raw_extracted_value,
               OTHER_FICTIONAL_ADDRESS);
  assert.equal(buildSyntheticPackage(state).documents[0].user_confirmed_value,
               FICTIONAL_ADDRESS);
});

test('edits invalidate prior review and a new approval is required', () => {
  let state = approveSyntheticPackage(readyStandard());
  assert.equal(state.package_approved, true);
  state = updateSyntheticFacts(state, { property_address: OTHER_FICTIONAL_ADDRESS });
  assert.equal(state.package_approved, false);
  assert.equal(evaluateSyntheticCase(state).status, 'needs_confirmation');
  state = confirmSyntheticFacts(state);
  assert.equal(evaluateSyntheticCase(state).status, 'needs_field_confirmation');
  assert.equal(buildSyntheticPackage(state), null);
});

test('fixture values are constrained; no free-form applicant or document uploads', () => {
  const current = createSyntheticCase();
  assert.throws(() => updateSyntheticFacts(current, { property_address: 'Real street 1' }),
                /pre-approved fictional/);
  assert.throws(() => updateSyntheticFacts(current, { previous_registration_context: 'admin' }),
                /pre-approved fictional/);
  assert.throws(() => updateSyntheticFacts(current, { owner_subject: 'not permitted' }),
                /pre-approved fictional/);
  assert.throws(() => updateSyntheticFacts(current, { property_address: null }),
                /pre-approved fictional/);
  assert.throws(() => createSyntheticCase('production'), /Unknown synthetic scenario/);
  assert.throws(() => confirmSyntheticDocumentField(current, FICTIONAL_ADDRESS),
                /documented synthetic sample/);
  assert.throws(() => reviewSyntheticDocument(current),
                /explicitly confirmed/);
});

test('mock source never claims official evidence or government action', () => {
  assert.equal(SYNTHETIC_EVIDENCE.official, false);
  assert.equal(SYNTHETIC_EVIDENCE.institution, 'SIMULATED — not Comune di Milano');
  assert.equal(Object.hasOwn(SYNTHETIC_EVIDENCE, 'official_url'), false);
  assert.match(DEMO_DISCLAIMER, /not legal advice/i);
  const packageData = buildSyntheticPackage(readyStandard());
  assert.equal(packageData.handoff, 'SIMULATED — no government portal connected');
  assert.equal(packageData.government_submission_status, 'NOT_SUBMITTED');
});


test('manipulated or incomplete scenario state fails closed', () => {
  const state = confirmSyntheticFacts(createSyntheticCase());
  const missing = {
    ...state,
    facts: { ...state.facts, household_context: undefined },
  };
  assert.equal(evaluateSyntheticCase(missing).status, 'needs_information');
  assert.equal(buildSyntheticPackage(missing), null);
  const invalidAddress = {
    ...state,
    facts: { ...state.facts, property_address: 'Actual resident address' },
  };
  assert.equal(evaluateSyntheticCase(invalidAddress).status, 'needs_information');
  assert.equal(buildSyntheticPackage(invalidAddress), null);
});
