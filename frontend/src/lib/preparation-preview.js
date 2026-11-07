/** Synthetic P0 preparation preview; always closed in production. */
export function preparationPreviewEnabled(env) {
  return env.VERCEL_ENV !== 'production' &&
    env.ENABLE_PREPARATION_UI === '1';
}

export function isPreparationFactsPayload(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const facts = value.confirmed_facts;
  if (!facts || typeof facts !== 'object' || Array.isArray(facts)) return false;
  const entries = Object.entries(facts);
  return entries.length <= 48 && entries.every(([key, raw]) =>
    /^[a-z][a-z0-9_]{0,63}$/.test(key) &&
    ((typeof raw === 'string' && raw.length > 0 && raw.length <= 240) ||
      typeof raw === 'boolean' ||
      (typeof raw === 'number' && Number.isSafeInteger(raw)))
  );
}

export function isPreparationPayload(operation, data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return false;
  if (operation === 'facts') return isPreparationFactsPayload(data);
  if (operation === 'guide') {
    return Object.keys(data).length === 2 &&
      typeof data.question === 'string' &&
      data.question.trim().length >= 2 &&
      data.question.length <= 180 &&
      (data.language === 'it' || data.language === 'en');
  }
  if (operation === 'package/approve') {
    return Object.keys(data).length === 1 &&
      typeof data.review_digest === 'string' &&
      /^[a-f0-9]{64}$/.test(data.review_digest);
  }
  if (operation === 'document/review') {
    return Object.keys(data).length === 1 && data.confirm_document === true;
  }
  if (operation === 'document/confirm-fields') {
    return Object.keys(data).sort().join(',') ===
       'confirmed_value,field_name,page,raw_value' &&
      data.field_name === 'property_address' &&
      typeof data.raw_value === 'string' && data.raw_value.length > 0 &&
      data.raw_value.length <= 180 &&
      typeof data.confirmed_value === 'string' &&
      data.confirmed_value.length > 0 && data.confirmed_value.length <= 180 &&
      Number.isInteger(data.page) && data.page >= 1 && data.page <= 15;
  }
  return false;
}

/**
 * User-reviewed, synthetic-only preparation artifact. Never represents an ANPR
 * form, municipal acceptance, or completed government submission.
 */
export function serializeReviewedPreparationPackage(data, reviewDigest) {
  if (!data || typeof data !== 'object' || Array.isArray(data) ||
      data.government_submission !== 'user_only_not_submitted' ||
      typeof reviewDigest !== 'string' || !/^[a-f0-9]{64}$/.test(reviewDigest)) {
    throw new Error('A currently reviewed preparation package is required');
  }
  return JSON.stringify({
    product: 'PracticaMIA',
    artifact_type: 'reviewed_preparation_summary',
    simulation_only: true,
    official_application_form: false,
    government_submission_status: 'NOT_SUBMITTED',
    review_digest: reviewDigest,
    package: data,
  }, null, 2) + '\n';
}
