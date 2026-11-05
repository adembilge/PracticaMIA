import test from 'node:test';
import assert from 'node:assert/strict';
import {
  assistantPreviewEnabled, isAssistantQuestionPayload,
} from '../src/lib/assistant-preview.js';

test('assistant is hidden on production and disabled by default', () => {
  assert.equal(assistantPreviewEnabled({}), false);
  assert.equal(assistantPreviewEnabled({
    ENABLE_ASSISTANT_UI: '1', VERCEL_ENV: 'production', NODE_ENV: 'production',
  }), false);
  assert.equal(assistantPreviewEnabled({
    ENABLE_ASSISTANT_UI: '1', VERCEL_ENV: 'preview', NODE_ENV: 'production',
  }), true);
  assert.equal(assistantPreviewEnabled({
    ENABLE_ASSISTANT_UI: '1', NODE_ENV: 'development',
  }), true);
  assert.equal(assistantPreviewEnabled({
    ENABLE_ASSISTANT_UI: 'true', VERCEL_ENV: 'preview',
  }), false);
});

test('assistant payload accepts only bounded questions and selected languages', () => {
  assert.equal(isAssistantQuestionPayload({ question: 'residenza', language: 'it' }), true);
  assert.equal(isAssistantQuestionPayload({ question: 'residence', language: 'en' }), true);
  for (const bad of [
    null, 1, [], 'residenza', {}, { question: 'x', language: 'it' },
    { question: 'hello', language: 'fr' },
    { question: 'a'.repeat(181), language: 'it' },
    { question: 'hello', language: 'it', jurisdiction: 'IT-RM-ROMA' },
  ]) assert.equal(isAssistantQuestionPayload(bad), false);
});
