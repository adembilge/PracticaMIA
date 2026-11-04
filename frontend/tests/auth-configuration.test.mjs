import test from 'node:test';
import assert from 'node:assert/strict';
import { hasAuthConfiguration, backendOrigin, sameOrigin } from '../src/lib/auth-configuration.js';

const working = {
  AUTH0_DOMAIN: 'example.eu.auth0.com',
  AUTH0_CLIENT_ID: 'example-client-id',
  AUTH0_CLIENT_SECRET: 'example-private-client-secret',
  AUTH0_SECRET: 'a'.repeat(64),
  AUTH0_AUDIENCE: 'https://api.practicamia.example',
};

test('login stays disabled without complete server-only configuration', () => {
  assert.equal(hasAuthConfiguration({}), false);
  for (const key of Object.keys(working)) {
    const invalid = { ...working };
    delete invalid[key];
    assert.equal(hasAuthConfiguration(invalid), false, key);
  }
  assert.equal(hasAuthConfiguration({ ...working, AUTH0_SECRET: 'short' }), false);
  assert.equal(hasAuthConfiguration({ ...working, AUTH0_DOMAIN: 'https://example.eu.auth0.com' }), false);
  assert.equal(hasAuthConfiguration(working), true);
});

test('backend proxy allows only explicit origin and requires HTTPS in production', () => {
  assert.equal(backendOrigin('https://api.practicamia.example'), 'https://api.practicamia.example');
  assert.equal(backendOrigin('http://localhost:8000', 'development'), 'http://localhost:8000');
  assert.equal(backendOrigin('http://127.0.0.1:8000', 'development'), 'http://127.0.0.1:8000');
  for (const value of [
    undefined, '', 'http://api.practicamia.example',
    'http://localhost:8000', 'https://api.practicamia.example/api',
    'https://api.practicamia.example?token=foo',
    'https://user:pass@api.practicamia.example',
    'javascript:alert(1)',
  ]) assert.equal(backendOrigin(value), null, String(value));
  assert.equal(backendOrigin('http://internal.example', 'development'), null);
});

test('case creation rejects missing and cross-origin requests', () => {
  const endpoint = 'https://practicamia.vercel.app/api/cases';
  assert.equal(sameOrigin(endpoint, null), false);
  assert.equal(sameOrigin(endpoint, 'https://attacker.example'), false);
  assert.equal(sameOrigin(endpoint, 'http://practicamia.vercel.app'), false);
  assert.equal(sameOrigin(endpoint, 'https://practicamia.vercel.app'), true);
});
