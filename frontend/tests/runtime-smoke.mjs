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
      ENABLE_REVIEW_UI: '1',
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

    const hiddenReviewer = await fetch(origin + '/knowledge/review');
    assert.equal(hiddenReviewer.status, 404, 'reviewer interface must stay hidden in production');
    const hiddenReviewApi = await fetch(origin + '/api/knowledge/review/browser-queue');
    assert.equal(hiddenReviewApi.status, 404, 'reviewer proxy must stay hidden in production');
    const hiddenFullReview = await fetch(
      origin + '/api/knowledge/review/versions/' + SAMPLE_ID,
    );
    assert.equal(hiddenFullReview.status, 404,
      'full reviewer evidence must not be public in production');

    const unauthenticated = await fetch(origin + '/api/cases');
    assert.equal(unauthenticated.status, 503, 'API must fail closed without Auth0 config');
    const csrf = await fetch(origin + '/api/cases', { method: 'POST' });
    assert.equal(csrf.status, 403, 'missing Origin must fail the CSRF gate');
    // Simulate a browser reaching "localhost" through the 127.0.0.1
    // loopback socket. Host and Origin must be exactly consistent.
    const browserOrigin = origin.replace('127.0.0.1', 'localhost');
    const browserHost = new URL(browserOrigin).host;
    const safeCreate = await fetch(origin + '/api/cases', {
      method: 'POST', headers: {
        Origin: browserOrigin, Host: browserHost,
        'Content-Type': 'application/json',
      },
      body: '{}',
    });
    assert.equal(safeCreate.status, 503,
      'a correctly matched Host and Origin must reach the auth fail-closed gate');
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

    const browserOrigin = origin.replace('127.0.0.1', 'localhost');
    const browserHost = new URL(browserOrigin).host;
    const sameOriginHeaders = {
      Origin: browserOrigin, Host: browserHost,
      'Content-Type': 'application/json',
    };
    const badPayload = await fetch(endpoint, {
      method: 'POST', headers: sameOriginHeaders,
      body: JSON.stringify({ question: 'residenza', language: 'it',
        jurisdiction: 'IT-RM-ROMA' }),
    });
    assert.equal(badPayload.status, 422, 'client may not select a jurisdiction');

    const unknown = await fetch(
      origin + '/api/cases/not-a-uuid/assistant/ask', {
        method: 'POST', headers: sameOriginHeaders,
        body: safePayload,
      },
    );
    assert.equal(unknown.status, 404, 'invalid case ID must fail');

    const noAuth = await fetch(endpoint, {
      method: 'POST', headers: sameOriginHeaders,
      body: safePayload,
    });
    assert.equal(noAuth.status, 503, 'preview cannot bypass absent Auth0 configuration');

    const reviewPage = await fetch(origin + '/knowledge/review');
    assert.equal(reviewPage.status, 200, 'preview reviewer interface should render');
    assert.match(await reviewPage.text(), /Official-source review/);
    const queue = await fetch(origin + '/api/knowledge/review/browser-queue');
    assert.equal(queue.status, 503, 'review queue cannot bypass absent Auth0');
    const full = await fetch(
      origin + '/api/knowledge/review/versions/' + SAMPLE_ID,
    );
    assert.equal(full.status, 503,
      'entire article capture cannot bypass missing Auth0 configuration');
    const pathTraversal = await fetch(
      origin + '/api/knowledge/review/versions/not-a-uuid',
    );
    assert.equal(pathTraversal.status, 404,
      'reviewer evidence proxy must reject invalid version IDs');
    const approvalEndpoint = origin + '/api/knowledge/review/approve-browser-batch';
    const reviewPayload = JSON.stringify({
      items: [{
        source_id: 'milano-residence-faq',
        version_id: SAMPLE_ID,
        expected_sha256: 'a'.repeat(64),
      }],
      review_note: 'Reviewed each captured official page and its applicability carefully.',
      confirmed_source_review: true,
    });
    const denied = await fetch(approvalEndpoint, {
      method: 'POST',
      headers: { Origin: 'https://untrusted.example', 'Content-Type': 'application/json' },
      body: reviewPayload,
    });
    assert.equal(denied.status, 403, 'review mutations reject cross-origin requests');
    const malformed = await fetch(approvalEndpoint, {
      method: 'POST', headers: sameOriginHeaders,
      body: JSON.stringify({ status: 'approved', actor_subject: 'forged' }),
    });
    assert.equal(malformed.status, 422, 'reviewer cannot forge status or identity');
    const unauthenticatedReview = await fetch(approvalEndpoint, {
      method: 'POST', headers: sameOriginHeaders, body: reviewPayload,
    });
    assert.equal(unauthenticatedReview.status, 503,
      'review approval must fail closed without Auth0 credentials');
  });
});
