/**
 * Prototype-only product scope filters. These are NOT official eligibility rules.
 * A matching result means "within our demo scenario", not legally eligible.
 */
export const SCOPE_FIELDS = [
  'registeredInMilan',
  'destinationInMilan',
  'applyingAlone',
  'joiningHousehold',
  'renting',
];

export const DEMO_ANSWERS = ['yes', 'yes', 'yes', 'no', 'yes'];

/** @param {(string | null | undefined)[]} answers */
export function classifyScope(answers) {
  for (let i = 0; i < SCOPE_FIELDS.length; i += 1) {
    if (!answers[i]) return 'incomplete';
    if (answers[i] === 'unsure') return 'needs_information';
    if (answers[i] !== DEMO_ANSWERS[i]) return 'unsupported';
  }
  return 'provisionally_in_scope';
}

/** @param {number} index @param {string} answer */
export function classifySingleAnswer(index, answer) {
  if (answer === 'unsure') return 'needs_information';
  if (answer !== DEMO_ANSWERS[index]) return 'unsupported';
  return 'pass';
}

/** @param {{ previousAddress?: string, newAddress?: string, movedOn?: string }} fields */
export function validateIntake(fields) {
  const issues = {};
  if (!fields.previousAddress?.trim()) issues.previousAddress = 'required';
  if (!fields.newAddress?.trim()) issues.newAddress = 'required';
  if (!fields.movedOn?.trim()) {
    issues.movedOn = 'required';
  } else if (!/^\d{4}-\d{2}-\d{2}$/.test(fields.movedOn) || !isRealDate(fields.movedOn)) {
    issues.movedOn = 'invalid';
  }
  return issues;
}

/** @param {{ previousAddress?: string, newAddress?: string, movedOn?: string }} fields */
export function sameAddressWarning(fields) {
  const a = fields.previousAddress?.trim().toLowerCase();
  const b = fields.newAddress?.trim().toLowerCase();
  return Boolean(a && b && a === b);
}

/** @param {string} value */
function isRealDate(value) {
  const [year, month, day] = value.split('-').map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() + 1 === month && parsed.getUTCDate() === day;
}
