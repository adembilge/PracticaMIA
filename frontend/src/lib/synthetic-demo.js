/**
 * Synthetic-only PracticaMIA demo. NO network, database, real legal rules,
 * municipal citations, authentic document extraction, or submission.
 *
 * This module is separate from the source-approved backend rules engine.
 * Every value and evidence reference is intentionally fabricated.
 */
export const DEMO_DISCLAIMER =
  'FICTIONAL SIMULATION. Not legal advice, official eligibility, OCR, an approved source, or government submission.';
export const DEMO_VERSION = 'SYNTHETIC-DEMO-2026-11-06-v1';
export const FICTIONAL_ADDRESS = 'Via Esempio Fittizia 10, Milano (SIMULATED)';
export const OTHER_FICTIONAL_ADDRESS = 'Via Esempio Fittizia 20, Milano (SIMULATED)';
export const PREVIOUS_FICTIONAL_ADDRESS = 'Via Esempio Fittizia 1, Milano (SIMULATED)';

export const SYNTHETIC_SCENARIOS = Object.freeze([
  {
    id: 'standard',
    title: 'Complete simulated application',
    subtitle: 'Review the ordinary happy path using invented facts and a sample document.',
  },
  {
    id: 'missing',
    title: 'Missing information',
    subtitle: 'The fictional procedure cannot be chosen without a required answer.',
  },
  {
    id: 'unsupported',
    title: 'Unsupported circumstances',
    subtitle: 'Show how the app refuses to prepare an unsupported simulated case.',
  },
  {
    id: 'conflict',
    title: 'Document discrepancy',
    subtitle: 'The sample document contains a different invented address; correction is required.',
  },
]);

export const SYNTHETIC_EVIDENCE = Object.freeze({
  id: 'SIM-EVIDENCE-001',
  title: 'FICTIONAL EXAMPLE — simulated procedure note',
  version: DEMO_VERSION,
  institution: 'SIMULATED — not Comune di Milano',
  official: false,
});

export const SYNTHETIC_REQUIREMENT = Object.freeze({
  rule_id: 'SIM-REQ-001',
  description: 'For this fictional demonstration, examine one sample housing note.',
  document_type: 'fictional_housing_note',
  evidence_ref: SYNTHETIC_EVIDENCE.id,
  official_requirement: false,
});

/** Entirely fictional test document. Not a valid application attachment. */
export const SYNTHETIC_DOCUMENT = Object.freeze({
  id: 'SIM-DOC-001',
  type: 'fictional_housing_note',
  name: 'Sample housing note — simulation only',
  owner: 'Persona Esempio (fictional)',
  source_page: 1,
  field_name: 'property_address',
  evidence_prefix: 'Property address: ',
  description: 'This is a simulated extraction of a supplied fixture, NOT live OCR.',
});

const VALID_REGISTRATIONS = new Set(['in_milan_example', 'unknown', 'arriving_abroad_example']);
const VALID_HOUSEHOLDS = new Set(['alone_example', 'joining_household_example']);
const VALID_HOUSING = new Set(['fictional_rental', 'unknown']);
const VALID_ADDRESSES = new Set([FICTIONAL_ADDRESS, OTHER_FICTIONAL_ADDRESS]);
export const SYNTHETIC_FACT_OPTIONS = Object.freeze({
  registrations: ['in_milan_example', 'unknown', 'arriving_abroad_example'],
  households: ['alone_example', 'joining_household_example'],
  housing: ['fictional_rental', 'unknown'],
  addresses: [FICTIONAL_ADDRESS, OTHER_FICTIONAL_ADDRESS],
});

function validScenario(id) {
  return SYNTHETIC_SCENARIOS.some((scenario) => scenario.id === id);
}

export function createSyntheticCase(scenarioId = 'standard') {
  if (!validScenario(scenarioId)) throw new Error('Unknown synthetic scenario');
  return {
    case_id: 'SIM-CASE-0001',
    scenario_id: scenarioId,
    applicant: 'Persona Esempio (fictional)',
    facts: {
      previous_registration_context:
        scenarioId === 'missing' ? 'unknown' :
        scenarioId === 'unsupported' ? 'arriving_abroad_example' : 'in_milan_example',
      household_context: 'alone_example',
      housing_arrangement: 'fictional_rental',
      previous_address: PREVIOUS_FICTIONAL_ADDRESS,
      property_address: FICTIONAL_ADDRESS,
      moved_on: '2026-11-01',
    },
    facts_confirmed: false,
    sample_loaded: false,
    extraction_value: null,
    confirmed_document_value: null,
    document_reviewed: false,
    package_approved: false,
  };
}

function clearDownstream(state, changes) {
  return {
    ...state,
    ...changes,
    package_approved: false,
  };
}

export function updateSyntheticFacts(state, fields) {
  const next = { ...state.facts, ...fields };
  if (!VALID_REGISTRATIONS.has(next.previous_registration_context) ||
      !VALID_HOUSEHOLDS.has(next.household_context) ||
      !VALID_HOUSING.has(next.housing_arrangement) ||
      next.previous_address !== PREVIOUS_FICTIONAL_ADDRESS ||
      !VALID_ADDRESSES.has(next.property_address) ||
      next.moved_on !== '2026-11-01') {
    throw new Error('Demo only accepts pre-approved fictional example values');
  }
  return clearDownstream(state, {
    facts: next,
    facts_confirmed: false,
    document_reviewed: false,
    confirmed_document_value: null,
  });
}

export function confirmSyntheticFacts(state) {
  // Confirmation is user action, not a determination of legal eligibility.
  return clearDownstream(state, { facts_confirmed: true });
}

export function loadSyntheticDocument(state) {
  // This reads a built-in fixture. It never reads, accepts or uploads user files.
  const extractionValue = state.scenario_id === 'conflict'
    ? OTHER_FICTIONAL_ADDRESS : FICTIONAL_ADDRESS;
  return clearDownstream(state, {
    sample_loaded: true,
    extraction_value: extractionValue,
    confirmed_document_value: null,
    document_reviewed: false,
  });
}

export function confirmSyntheticDocumentField(state, correctedAddress) {
  if (!state.sample_loaded || !VALID_ADDRESSES.has(correctedAddress)) {
    throw new Error('Only documented synthetic sample addresses can be confirmed');
  }
  return clearDownstream(state, {
    confirmed_document_value: correctedAddress,
    document_reviewed: false,
  });
}

export function reviewSyntheticDocument(state) {
  if (!state.sample_loaded || !state.confirmed_document_value) {
    throw new Error('Review requires an explicitly confirmed extracted field');
  }
  return clearDownstream(state, { document_reviewed: true });
}

export function evaluateSyntheticCase(state) {
  const facts = state.facts;
  const missing = [];
  const evidence = SYNTHETIC_EVIDENCE;
  const base = {
    simulated: true,
    disclaimer: DEMO_DISCLAIMER,
    ruleset_version: DEMO_VERSION,
    evidence: [],
    checklist: [],
    missing_fields: [],
    blocking_issues: [],
  };
  if (facts.previous_registration_context === 'arriving_abroad_example' ||
      facts.household_context === 'joining_household_example') {
    return {
      ...base,
      decision: 'unsupported',
      status: 'unsupported',
      blocking_issues: ['Scenario intentionally excluded from this fictional walkthrough'],
    };
  }
  if (facts.previous_registration_context === 'unknown') missing.push('previous_registration_context');
  if (facts.housing_arrangement === 'unknown') missing.push('housing_arrangement');
  if (missing.length) {
    return {
      ...base, decision: 'needs_information', status: 'needs_information',
      missing_fields: missing,
      blocking_issues: ['Confirm the missing simulated route facts'],
    };
  }
  if (!state.facts_confirmed) {
    return {
      ...base, decision: 'needs_confirmation', status: 'needs_confirmation',
      blocking_issues: ['Confirm the fictional intake facts'],
    };
  }
  const supported = {
    ...base, decision: 'supported',
    evidence: [evidence],
    checklist: [SYNTHETIC_REQUIREMENT],
  };
  if (!state.sample_loaded) {
    return {
      ...supported, status: 'needs_documents',
      blocking_issues: ['Load the built-in fictional document'],
    };
  }
  if (!state.confirmed_document_value) {
    return {
      ...supported, status: 'needs_field_confirmation',
      blocking_issues: ['Confirm or correct the simulated document extraction'],
    };
  }
  if (!state.document_reviewed) {
    return {
      ...supported, status: 'needs_document_review',
      blocking_issues: ['Explicitly review the sample document'],
    };
  }
  if (state.confirmed_document_value !== facts.property_address) {
    return {
      ...supported, status: 'needs_review',
      blocking_issues: ['Conflicting property addresses in the fictional intake and sample document'],
    };
  }
  return {
    ...supported,
    status: state.package_approved ? 'simulated_handoff' : 'reviewable',
    blocking_issues: [],
  };
}

export function buildSyntheticPackage(state) {
  const status = evaluateSyntheticCase(state).status;
  if (status !== 'reviewable' && status !== 'simulated_handoff') return null;
  return {
    simulation_only: true,
    applicant: state.applicant,
    synthetic_case_id: state.case_id,
    procedure: 'SIMULATED MILAN RESIDENCE-CHANGE PREPARATION',
    ruleset_version: DEMO_VERSION,
    facts: { ...state.facts },
    checklist: [{
      ...SYNTHETIC_REQUIREMENT,
      state: 'sample_document_reviewed',
    }],
    evidence: [SYNTHETIC_EVIDENCE],
    documents: [{
      ...SYNTHETIC_DOCUMENT,
      raw_extracted_value: state.extraction_value,
      user_confirmed_value: state.confirmed_document_value,
      user_reviewed: true,
      extraction_method: 'simulated_fixture_not_ocr',
    }],
    reviewed_by: state.package_approved ? 'fictional_demo_participant' : null,
    government_submission_status: 'NOT_SUBMITTED',
    handoff: 'SIMULATED — no government portal connected',
    disclaimer: DEMO_DISCLAIMER,
  };
}

export function approveSyntheticPackage(state) {
  if (evaluateSyntheticCase(state).status !== 'reviewable') {
    throw new Error('Cannot approve a blocked or already approved simulated package');
  }
  return { ...state, package_approved: true };
}

export function syntheticDocumentText(state) {
  if (!state.sample_loaded) return '';
  return [
    'FICTIONAL SAMPLE DOCUMENT — NOT VALID FOR ANY ADMINISTRATIVE PROCEDURE',
    'Reference: ' + SYNTHETIC_DOCUMENT.id,
    'Document type: Synthetic housing note',
    'Applicant: ' + state.applicant,
    SYNTHETIC_DOCUMENT.evidence_prefix + state.extraction_value,
    'PAGE 1 — All content invented for a user-interface demonstration.',
  ].join('\n');
}
