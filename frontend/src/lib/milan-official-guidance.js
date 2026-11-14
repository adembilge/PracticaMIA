/**
 * Published public reference URLs only. This is NOT an approved-source
 * registry or an applicant-specific eligibility or document checklist.
 */
export const MILAN_OFFICIAL_LINKS = Object.freeze({
  service: 'https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza',
  faq: 'https://servizicrm.comune.milano.it/centro-supporto/KA-00371/',
  anpr: 'https://www.anagrafenazionale.interno.it/',
});

export const MILAN_GUIDANCE_SNAPSHOT = '2026-11-08';

export function isOfficialGuidanceUrl(value) {
  if (typeof value !== 'string') return false;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' &&
      !url.username && !url.password && !url.search && !url.hash &&
      ['www.comune.milano.it', 'servizicrm.comune.milano.it',
        'www.anagrafenazionale.interno.it'].includes(url.hostname);
  } catch {
    return false;
  }
}
