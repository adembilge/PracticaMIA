/** Only allow an explicitly configured development or preview assistant UI. */
export function assistantPreviewEnabled(env) {
  return env.ENABLE_ASSISTANT_UI === '1'
    && (env.VERCEL_ENV === 'preview'
      || (env.NODE_ENV === 'development' && !env.VERCEL_ENV));
}

export function isAssistantQuestionPayload(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  if (keys.length !== 2 || !keys.includes('question') || !keys.includes('language')) return false;
  if (value.language !== 'it' && value.language !== 'en') return false;
  return typeof value.question === 'string'
    && value.question.trim().length >= 2
    && value.question.length <= 180;
}
