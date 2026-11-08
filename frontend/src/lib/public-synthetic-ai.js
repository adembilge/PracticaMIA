/** Fixed, non-personal illustrative prompts for the production portfolio MVP.
 * No client-authored text, case facts, or uploaded documents reach a model.
 */
export const PUBLIC_AI_TOPICS = Object.freeze(['scope', 'documents', 'handoff']);

const examples = Object.freeze({
  scope: 'A completely fictional person already registered in Milan moves alone to another invented rental address within Milan. Explain how a workflow app should gather missing information and defer unsupported situations. Do not specify any actual legal eligibility rules.',
  documents: 'In a fictional workflow, an invented housing-note attachment contains an example address that disagrees with an invented case summary. Explain why user confirmation and discrepancy resolution should occur before an example package is prepared. No official document requirements.',
  handoff: 'Explain the difference between an example package prepared in an app, the user reviewing it, the user separately submitting via an official external portal, and the authority later processing it. Do not imply anything was officially submitted.',
});

export function publicSyntheticAIEnabled(env) {
  return env.VERCEL_ENV === 'production' &&
    env.ENABLE_PUBLIC_SYNTHETIC_AI === '1' &&
    typeof env.OPENROUTER_API_KEY === 'string' &&
    env.OPENROUTER_API_KEY.length >= 32;
}

export function validatePublicAIRequest(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  if (Object.keys(value).sort().join(',') !== 'language,topic') return null;
  if (value.language !== 'en' && value.language !== 'it') return null;
  if (!PUBLIC_AI_TOPICS.includes(value.topic)) return null;
  return {topic: value.topic, language: value.language};
}

export function syntheticAIMessages(request) {
  const input = validatePublicAIRequest(request);
  if (!input) return null;
  return [
    {role: 'system', content:
      'You are demonstrating an educational AI feature in a FICTIONAL municipal-case workflow. ' +
      'Every rule, document, citation, and person in this example is invented. ' +
      'Explain product steps only. Do not state Italian eligibility requirements, timelines, ' +
      'mandatory documents, legal advice, or claim verification of real sources. ' +
      'Never say any government application was submitted. ' +
      'No personal information is available. ' +
      (input.language === 'it' ? 'Respond in Italian.' : 'Respond in English.') +
      ' Limit response to 110 words, plain text.'},
    {role: 'user', content: examples[input.topic]},
  ];
}
