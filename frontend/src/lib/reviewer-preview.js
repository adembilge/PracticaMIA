/** Reviewer controls are deliberately absent from Vercel production. */
export function reviewerPreviewEnabled(env) {
  return env.ENABLE_REVIEW_UI === '1'
    && (env.VERCEL_ENV === 'preview'
      || (env.NODE_ENV === 'development' && !env.VERCEL_ENV));
}

/** Reject extra fields: the browser cannot select reviewer identity or source status. */
export function isBrowserReviewBatchPayload(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  if (keys.length !== 3 || !['items', 'review_note', 'confirmed_source_review']
    .every((name) => keys.includes(name))) return false;
  if (value.confirmed_source_review !== true) return false;
  if (typeof value.review_note !== 'string'
    || value.review_note.trim().length < 30
    || value.review_note.length > 450) return false;
  if (!Array.isArray(value.items) || value.items.length < 1
    || value.items.length > 15) return false;
  const ids = new Set(), sourceIds = new Set();
  for (const item of value.items) {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return false;
    const fields = Object.keys(item);
    if (fields.length !== 3 ||
      !['source_id', 'version_id', 'expected_sha256']
        .every((name) => fields.includes(name))) return false;
    if (typeof item.source_id !== 'string'
      || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(item.source_id)
      || item.source_id.length > 96) return false;
    if (typeof item.version_id !== 'string'
      || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
        .test(item.version_id)) return false;
    if (typeof item.expected_sha256 !== 'string'
      || !/^[0-9a-f]{64}$/.test(item.expected_sha256)) return false;
    if (ids.has(item.version_id) || sourceIds.has(item.source_id)) return false;
    ids.add(item.version_id);
    sourceIds.add(item.source_id);
  }
  return true;
}

/** Human-authenticated review of one exact PDF version, never an auto approval. */
export function isIndividualPdfReviewPayload(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  if (keys.length !== 3 ||
      !['expected_sha256', 'review_note', 'confirmed_source_review']
        .every((key) => keys.includes(key))) return false;
  if (value.confirmed_source_review !== true) return false;
  if (typeof value.expected_sha256 !== 'string' ||
      !/^[0-9a-f]{64}$/.test(value.expected_sha256)) return false;
  if (typeof value.review_note !== 'string' ||
      value.review_note.trim().length < 30 || value.review_note.length > 450) {
    return false;
  }
  return true;
}
