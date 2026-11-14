import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MILAN_OFFICIAL_LINKS, MILAN_GUIDANCE_SNAPSHOT, isOfficialGuidanceUrl,
} from '../src/lib/milan-official-guidance.js';

test('Milan production guidance references only official HTTPS destinations', () => {
  assert.equal(MILAN_GUIDANCE_SNAPSHOT, '2026-11-08');
  for (const url of Object.values(MILAN_OFFICIAL_LINKS)) {
    assert.equal(isOfficialGuidanceUrl(url), true);
  }
  assert.equal(Object.keys(MILAN_OFFICIAL_LINKS).length, 3);
});

test('external links, credentials and misleading domains are excluded', () => {
  for (const url of [
    'https://comune.milano.it.attacker.example/path',
    'http://www.comune.milano.it/servizi',
    'https://a@www.comune.milano.it/',
    'https://www.comune.milano.it/x?next=evil',
    'javascript:alert(1)',
    '',
  ]) assert.equal(isOfficialGuidanceUrl(url), false);
});
