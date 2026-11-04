import { classifySingleAnswer } from './flow.js';

/** @typedef {'yes' | 'no' | 'unsure'} Answer */
export const SCOPE_QUESTION_COUNT = 5;

/** @param {unknown} value @returns {value is Answer} */
export function isScopeAnswer(value) {
  return value === 'yes' || value === 'no' || value === 'unsure';
}

/** @param {unknown} value @returns {value is { answers: Answer[] }} */
export function isScopePayload(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  const record = /** @type {Record<string, unknown>} */ (value);
  return Object.keys(record).length === 1 && Array.isArray(record.answers)
    && record.answers.length >= 1 && record.answers.length <= SCOPE_QUESTION_COUNT
    && record.answers.every(isScopeAnswer);
}

/** UUID validated before adding an untrusted route segment to the backend URL. 
 *  @param {string} id
 */
export function isCaseId(id) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
}

/** @param {Answer[]} answers */
export function firstUnresolvedQuestion(answers) {
  for (let i = 0; i < Math.min(answers.length, SCOPE_QUESTION_COUNT); i += 1) {
    if (classifySingleAnswer(i, answers[i]) !== 'pass') return i;
  }
  return Math.min(answers.length, SCOPE_QUESTION_COUNT - 1);
}

/** Editing an earlier answer discards downstream answers so they cannot silently remain confirmed.
 *  @param {Answer[]} previous
 *  @param {number} index
 *  @param {Answer} choice
 *  @returns {Answer[]}
 */
export function nextScopeAnswers(previous, index, choice) {
  if (!Number.isInteger(index) || index < 0 || index >= SCOPE_QUESTION_COUNT
      || index > previous.length || !isScopeAnswer(choice)) {
    throw new Error('Invalid scope answer position');
  }
  if (previous[index] === choice) return [...previous];
  return [...previous.slice(0, index), choice];
}
