/** Case-aware, non-authoritative guidance derived from SAVED backend scope answers.
 * Never infer citizenship, a registered lease, accepted attachments or eligibility
 * from five product scope questions. No personal case facts are sent to a model.
 */
import { classifyScope, DEMO_ANSWERS } from './flow.js';

export const CASE_GUIDANCE_TOPICS = Object.freeze(['next_step', 'explain_status']);
export const CASE_GUIDANCE_STATUSES = Object.freeze([
  'incomplete', 'needs_information', 'unsupported', 'provisionally_in_scope',
]);

export const SCOPE_LABELS = Object.freeze({
  en: Object.freeze([
    'Already registered as a Milan resident',
    'Moving to another address in Milan',
    'Applying only for yourself',
    'Joining an existing registered household',
    'Renting the new home',
  ]),
  it: Object.freeze([
    'Già residente a Milano',
    'Trasferimento a un altro indirizzo a Milano',
    'Domanda presentata soltanto per te',
    'Ingresso in una famiglia anagrafica esistente',
    'Nuova abitazione in affitto',
  ]),
});

export function parseStoredCase(value, requestedId) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      typeof requestedId !== 'string' || value.id !== requestedId ||
      value.procedure !== 'milan_residence_change' ||
      !Array.isArray(value.scope_answers) || value.scope_answers.length > 5 ||
      value.scope_answers.some(x => !['yes','no','unsure'].includes(x))) return null;
  const calculated = value.scope_answers.length === 0
    ? 'draft' : classifyScope(value.scope_answers);
  if (value.status !== calculated) return null;
  return {
    id: value.id,
    status: calculated,
    answers: [...value.scope_answers],
  };
}

export function validateCaseGuidanceRequest(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  if (Object.keys(value).sort().join(',') !== 'language,topic') return null;
  if (!CASE_GUIDANCE_TOPICS.includes(value.topic) ||
      !['en', 'it'].includes(value.language)) return null;
  return {topic: value.topic, language: value.language};
}

export function getCaseGuidancePlan(caseRecord, language = 'en') {
  if (!caseRecord || !['en', 'it'].includes(language) ||
      !Array.isArray(caseRecord.answers) || caseRecord.answers.length > 5 ||
      caseRecord.answers.some(a => !['yes','no','unsure'].includes(a))) return null;
  const expectedStatus = caseRecord.answers.length === 0
    ? 'draft' : classifyScope(caseRecord.answers);
  if (caseRecord.status !== expectedStatus) return null;

  const it = language === 'it';
  const idx = DEMO_ANSWERS.findIndex((expected, i) =>
    i >= caseRecord.answers.length || caseRecord.answers[i] !== expected);
  const status = expectedStatus === 'draft' ? 'incomplete' : expectedStatus;
  let summary, nextStep;
  if (status === 'incomplete') {
    summary = it ? 'La pratica ha ancora domande iniziali senza risposta.' :
      'Your saved case has unanswered initial questions.';
    nextStep = it ? 'Rispondi alla domanda successiva. Puoi modificare le risposte già salvate.' :
      'Answer the next question. You can edit previously saved answers.';
  } else if (status === 'needs_information') {
    summary = it ? 'Hai indicato che non conosci una risposta necessaria per continuare la verifica dell’ambito.' :
      'One of your saved scope answers is uncertain.';
    nextStep = it ? 'Chiarisci la risposta evidenziata prima di proseguire.' :
      'Clarify the highlighted answer before continuing.';
  } else if (status === 'unsupported') {
    summary = it ? 'La situazione descritta non corrisponde all’unico scenario gestito da questa demo. Non significa che la domanda sia inammissibile.' :
      'Your situation differs from this product’s supported example. This does not mean your official application is ineligible.';
    nextStep = it ? 'Controlla direttamente le istruzioni ufficiali o correggi la risposta se era inesatta.' :
      'Consult the official service or correct the answer if it was inaccurate.';
  } else {
    summary = it ? 'Le cinque risposte salvate corrispondono allo scenario limitato della demo; non sono una verifica dei requisiti legali.' :
      'Your five saved answers match this demo’s narrow scenario; they do not establish legal eligibility.';
    nextStep = it ? 'Consulta le fonti comunali e ANPR. Nazionalità, contratto registrato e allegati applicabili non sono stati verificati.' :
      'Review the official Milan and ANPR guidance. Citizenship, rental registration and applicable attachments have not been verified.';
  }
  return {
    status,
    completed: status === 'provisionally_in_scope',
    next_question_index: idx < 0 ? null : idx,
    answered_count: caseRecord.answers.length,
    summary,
    next_step: nextStep,
    answers: caseRecord.answers.map((value, i) => ({
      question: SCOPE_LABELS[language][i],
      answer: value,
    })),
    authoritative_check: false,
    official_submission: false,
    personalized_documents_verified: false,
  };
}

export function makeCaseGuidanceMessages(plan, request) {
  const parsed = validateCaseGuidanceRequest(request);
  if (!plan || !parsed || !CASE_GUIDANCE_STATUSES.includes(plan.status) ||
      !Number.isInteger(plan.answered_count) || plan.answered_count < 0 ||
      plan.answered_count > 5 ||
      (plan.next_question_index !== null &&
       (!Number.isInteger(plan.next_question_index) || plan.next_question_index < 0 ||
        plan.next_question_index > 4))) return null;
  // Only these fixed, abstract product-stage descriptions are sent to OpenRouter.
  // Do NOT interpolate the user's answers, case ID, name, dates or documents.
  const stages = {
    incomplete: 'The product is still gathering its five initial scope answers.',
    needs_information: 'A user needs to clarify an uncertain scope answer.',
    unsupported: 'The saved answers describe a case outside the limited product demo. This is not legal ineligibility.',
    provisionally_in_scope: 'All five product scope questions match the demonstration. Legal eligibility and documents remain unverified.',
  };
  const topic = parsed.topic === 'next_step'
    ? 'Explain why the user should take the next product workflow step.'
    : 'Explain what the product scope status means and does not mean.';
  return [
    {role: 'system', content:
      'You explain navigation through a limited Milan residence-change web prototype. ' +
      'You are NOT an official authority, lawyer, source-of-truth or eligibility evaluator. ' +
      'The input contains only an abstract product state, no personal data or documents. ' +
      'Do not invent or suggest alternative identity or housing proofs, required attachments, ' +
      'deadlines, municipal approval, manual review queues or official submission. ' +
      'Do not claim records or sources were checked or verified. ' +
      'Only explain the next product action in one or two short sentences, plain text. ' +
      (parsed.language === 'it' ? 'Respond in Italian.' : 'Respond in English.')},
    {role: 'user', content: stages[plan.status] + ' ' +
      (plan.next_question_index === null ? 'All scope questions have been answered.' :
        'The next product question has number ' + (plan.next_question_index + 1) + '.') +
      ' ' + topic},
  ];
}
