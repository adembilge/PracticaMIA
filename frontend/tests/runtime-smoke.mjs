/** Real localhost HTTP smoke tests against a built Next.js server.

No external API tokens, government data, or Auth0 credentials. We deliberately
request ENABLE_ASSISTANT_UI=1 under a production environment to check that the
preview remains inaccessible; then test a preview with no auth configured.
Run after `npm run build`.
*/
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { createServer } from 'node:net';
import { once } from 'node:events';

async function freePort() {
  const server = createServer();
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const port = server.address().port;
  await new Promise((resolve) => server.close(resolve));
  return port;
}

async function withServer(overrides, fn) {
  const port = await freePort();
  const origin = 'http://127.0.0.1:' + port;
  const child = spawn(process.execPath, [
    'node_modules/next/dist/bin/next', 'start', '-p', String(port),
    '-H', '127.0.0.1',
  ], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      NODE_ENV: 'production',
      VERCEL_ENV: 'production',
      ENABLE_ASSISTANT_UI: '1',
      AUTH0_DOMAIN: '',
      AUTH0_CLIENT_ID: '',
      AUTH0_CLIENT_SECRET: '',
      AUTH0_SECRET: '',
      AUTH0_AUDIENCE: '',
      BACKEND_API_URL: '',
      ...overrides,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let output = '';
  for (const stream of [child.stdout, child.stderr]) {
    stream.on('data', (chunk) => { output = (output + chunk.toString()).slice(-5000); });
  }
  try {
    let started = false;
    for (let n = 0; n < 100; n += 1) {
      if (child.exitCode !== null) break;
      try {
        const response = await fetch(origin + '/', {
          signal: AbortSignal.timeout(1200),
        });
        if (response.status === 200) {
          started = true;
          break;
        }
      } catch { /* Starting server. */ }
      await sleep(180);
    }
    assert.equal(started, true, 'Next.js failed to start: ' + output);
    return await fn(origin);
  } finally {
    if (child.exitCode === null) {
      const stopped = once(child, 'exit').catch(() => null);
      child.kill('SIGTERM');
      await Promise.race([stopped, sleep(2500)]);
      if (child.exitCode === null) child.kill('SIGKILL');
    }
  }
}

const SAMPLE_ID = '00000000-0000-0000-0000-000000000001';

test('production-mode HTTP: public demo pages work and assistant stays hidden', {
  timeout: 45000,
}, async () => {
  await withServer({}, async (origin) => {
    for (const pathname of [
      '/', '/account', '/cases/new', '/cases/demo', '/cases/saved',
      '/cases/' + SAMPLE_ID,
    ]) {
      const response = await fetch(origin + pathname);
      assert.equal(response.status, 200, pathname);
      assert.match(response.headers.get('content-type') || '', /text\/html/);
    }
    const hidden = await fetch(origin + '/cases/' + SAMPLE_ID + '/assistant');
    assert.equal(hidden.status, 404, 'preview UI must not be available in production');
    const hiddenApi = await fetch(
      origin + '/api/cases/' + SAMPLE_ID + '/assistant/ask',
      { method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: 'residenza', language: 'it' }) },
    );
    assert.equal(hiddenApi.status, 404, 'preview proxy must remain disabled');

    const unauthenticated = await fetch(origin + '/api/cases');
    assert.equal(unauthenticated.status, 503, 'API must fail closed without Auth0 config');
    const csrf = await fetch(origin + '/api/cases', { method: 'POST' });
    assert.equal(csrf.status, 403, 'missing Origin must fail the CSRF gate');
    const safeCreate = await fetch(origin + '/api/cases', {
      method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json' },
      body: '{}',
    });
    assert.equal(safeCreate.status, 503, 'no unauthenticated case creation');
  });
});

test('preview-mode HTTP: interface renders but input and authentication gates hold', {
  timeout: 45000,
}, async () => {
  await withServer({ VERCEL_ENV: 'preview' }, async (origin) => {
    const url = origin + '/cases/' + SAMPLE_ID + '/assistant';
    const available = await fetch(url);
    assert.equal(available.status, 200, 'preview UI should render for a valid demo case');
    assert.match(await available.text(), /Evidence assistant preview|Anteprima assistente/);

    const endpoint = origin + '/api/cases/' + SAMPLE_ID + '/assistant/ask';
    const safePayload = JSON.stringify({ question: 'residenza', language: 'it' });
    const crossOrigin = await fetch(endpoint, {
      method: 'POST', headers: { Origin: 'https://untrusted.example',
        'Content-Type': 'application/json' }, body: safePayload,
    });
    assert.equal(crossOrigin.status, 403, 'cross-origin request must fail');

    const badPayload = await fetch(endpoint, {
      method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: 'residenza', language: 'it',
        jurisdiction: 'IT-RM-ROMA' }),
    });
    assert.equal(badPayload.status, 422, 'client may not select a jurisdiction');

    const unknown = await fetch(
      origin + '/api/cases/not-a-uuid/assistant/ask', {
        method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json' },
        body: safePayload,
      },
    );
    assert.equal(unknown.status, 404, 'invalid case ID must fail');

    const noAuth = await fetch(endpoint, {
      method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json' },
      body: safePayload,
    });
    assert.equal(noAuth.status, 503, 'preview cannot bypass absent Auth0 configuration');
  });
});
