/** Release-gated real-document vault. Never enable from browser inputs. */
export const PRIVATE_DOCUMENT_CONSENT_VERSION = 'private-documents-2026-11-v1';
export const PRIVATE_DOCUMENT_MAX_BYTES = 2 * 1024 * 1024;
export const PRIVATE_DOCUMENT_CATEGORIES = Object.freeze([
  'housing_document', 'identity_document', 'other_supporting_document',
]);

export function privateDocumentsUiEnabled(env) {
  return env.VERCEL_ENV === 'production' &&
    env.ENABLE_PRIVATE_DOCUMENT_UI === '1' &&
    env.PRIVATE_DOCUMENT_PRIVACY_APPROVED === '1' &&
    Boolean(env.PRIVATE_DOCUMENT_CONTROLLER?.trim()) &&
    Boolean(env.PRIVATE_DOCUMENT_CONTACT?.trim());
}

export function isPrivateUploadMeta(category, privacyAck, version, fileSize, mime) {
  return PRIVATE_DOCUMENT_CATEGORIES.includes(category) &&
    privacyAck === 'true' &&
    version === PRIVATE_DOCUMENT_CONSENT_VERSION &&
    Number.isSafeInteger(fileSize) && fileSize > 0 &&
    fileSize <= PRIVATE_DOCUMENT_MAX_BYTES &&
    ['application/pdf','image/png','image/jpeg'].includes(mime);
}
