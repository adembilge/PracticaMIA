/**
 * The published sources displayed in the first Milan beta case.
 * The archive is an approved snapshot, NOT a live government edition.
 */
export const FIRST_ROUTE_SOURCE_LINKS = Object.freeze({
  'milano-italian-residence-change': Object.freeze({
    url: 'https://servizicrm.comune.milano.it/centro-supporto/KA-00371/',
    kind: 'municipal',
  }),
  'anpr-public-docs-residence-guide': Object.freeze({
    url: 'https://public-anpr.github.io/anpr-docs-cittadino/src/docs/guide/guida_compilazione_cambio_residenza.pdf',
    kind: 'archived',
  }),
});

export function selectReviewedFirstRouteSources(payload) {
  if (!payload || payload.status !== 'approved_sources_available' ||
      !Array.isArray(payload.sources)) return [];
  const unique = new Set();
  return payload.sources.filter((source) => {
    if (!source || typeof source !== 'object') return false;
    const expected = FIRST_ROUTE_SOURCE_LINKS[source.source_id];
    if (!expected || source.official_url !== expected.url ||
        source.procedure_id !== 'milan_residence_change' ||
        source.jurisdiction !== 'IT-MI-MILANO' ||
        !/^[0-9a-f]{64}$/.test(source.content_sha256 ?? '') ||
        typeof source.reviewed_at !== 'string' ||
        !source.source_version_id || unique.has(source.source_id)) return false;
    unique.add(source.source_id);
    return true;
  });
}
