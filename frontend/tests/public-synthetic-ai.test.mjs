import assert from 'node:assert/strict';
import test from 'node:test';
import {
  publicSyntheticAIEnabled, validatePublicAIRequest, syntheticAIMessages,
} from '../src/lib/public-synthetic-ai.js';

test('production-only fictional model feature fails closed by default', () => {
  assert.equal(publicSyntheticAIEnabled({ VERCEL_ENV: 'production' }), false);
  assert.equal(publicSyntheticAIEnabled({ VERCEL_ENV: 'production', ENABLE_PUBLIC_SYNTHETIC_AI: '1' }), false);
  assert.equal(publicSyntheticAIEnabled({ VERCEL_ENV: 'preview', ENABLE_PUBLIC_SYNTHETIC_AI: '1', OPENROUTER_API_KEY: 'x'.repeat(40) }), false);
  assert.equal(publicSyntheticAIEnabled({ VERCEL_ENV: 'production', ENABLE_PUBLIC_SYNTHETIC_AI: '1', OPENROUTER_API_KEY: 'x'.repeat(40) }), true);
});

test('model requests allow exactly one of three fictional topics in two languages', () => {
  for (const topic of ['scope', 'documents', 'handoff']) {
    for (const language of ['en', 'it']) {
      assert.deepEqual(validatePublicAIRequest({topic, language}), {topic,language});
      const messages = syntheticAIMessages({topic, language});
      assert.equal(messages.length,2);
      assert.match(messages[0].content,/FICTIONAL/);
      assert.match(messages[0].content,/Never say any government application was submitted/);
      assert.ok(messages[1].content.length >= 60);
      assert.ok(!JSON.stringify(messages).includes('CONFIDENTIAL'));
    }
  }
});

test('arbitrary free text or case data never enter the model prompt', () => {
  for(const payload of [
    null, [], {}, {topic:'unknown',language:'en'}, {topic:'documents'},
    {topic:'scope',language:'de'}, {topic:'scope',language:'en',question:'My real home is...'},
    {topic:'handoff',language:'en',facts:{name:'CONFIDENTIAL'}},
  ]) {
    assert.equal(validatePublicAIRequest(payload),null);
    assert.equal(syntheticAIMessages(payload),null);
  }
});
