/** Intentionally excludes addresses, identity numbers, names, free-text notes.
 * This first intake stage collects only narrow categorical case facts and date.
 */
export const INTAKE_FIELDS = Object.freeze([
  'citizenship_class', 'registration_context', 'destination_municipality',
  'household_scope', 'housing_basis',
]);
export const INTAKE_OPTIONS = Object.freeze({
  citizenship_class: Object.freeze(['italian','non_italian','unknown']),
  registration_context: Object.freeze(['already_registered_in_italy','arrival_from_abroad','unknown']),
  destination_municipality: Object.freeze(['milano','other','unknown']),
  household_scope: Object.freeze(['individual_no_aggregation','joining_household','multi_person','unknown']),
  housing_basis: Object.freeze(['registered_private_rental','owner','guest','other','unknown']),
});
export const FIRST_ROUTE_FACTS = Object.freeze({
  citizenship_class:'italian',
  registration_context:'already_registered_in_italy',
  destination_municipality:'milano',
  household_scope:'individual_no_aggregation',
  housing_basis:'registered_private_rental',
});

export function isRealCalendarDate(s) {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const [year,month,day] = s.split('-').map(Number);
  if (year < 1900 || year > 2100) return false;
  const d = new Date(Date.UTC(year,month-1,day));
  return d.getUTCFullYear()===year && d.getUTCMonth()===month-1 &&
    d.getUTCDate()===day;
}

/** @param {unknown} raw */
export function isCaseIntakePayload(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return false;
  const payload = /** @type {Record<string,unknown>} */ (raw);
  if (Object.keys(payload).sort().join(',') !== 'confirm,facts' ||
      typeof payload.confirm !== 'boolean' || !payload.facts ||
      typeof payload.facts !== 'object' || Array.isArray(payload.facts)) return false;
  const facts = /** @type {Record<string,unknown>} */ (payload.facts);
  const permitted = [...INTAKE_FIELDS,'move_in_date'];
  return Object.entries(facts).length<=6 &&
    Object.entries(facts).every(([k,v])=>
      permitted.includes(k) && typeof v === 'string' &&
      (k === 'move_in_date' ? isRealCalendarDate(v) :
        INTAKE_OPTIONS[k]?.includes(v))) &&
    (!payload.confirm ||
      INTAKE_FIELDS.every(k=>typeof facts[k]==='string' &&
        facts[k] !== 'unknown'));
}

export function firstRouteIntakeState(facts, confirmed) {
  if (!facts || typeof facts!=='object') return 'incomplete';
  if (INTAKE_FIELDS.some(k=>!facts[k] || facts[k]==='unknown')) return 'incomplete';
  if (INTAKE_FIELDS.some(k=>facts[k]!==FIRST_ROUTE_FACTS[k])) return 'outside_first_scenario';
  return confirmed?'confirmed':'needs_confirmation';
}
