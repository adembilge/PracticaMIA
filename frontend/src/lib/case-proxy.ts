import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { headers as requestHeaders } from 'next/headers';
import { auth0 } from '@/lib/auth0';
import { backendOrigin, sameOrigin } from '@/lib/auth-configuration.js';

const headers = { 'Cache-Control': 'private, no-store' };
type CaseMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE';

export function caseError(message: string, status: number) {
  return NextResponse.json({ error: message }, { status, headers });
}

/** Mutations must originate from the canonical same-origin browser UI. */
export function rejectCrossOrigin(request: NextRequest) {
  return sameOrigin(request.url, request.headers.get('origin'))
    ? null : caseError('Forbidden origin', 403);
}

/** Never expose Auth0 API tokens to the browser. All backend requests run on the server. */
export async function proxyCaseRequest(method: CaseMethod, path: string, payload?: unknown, timeoutMs = 8000) {
  if (!auth0) return caseError('Service not configured', 503);
  const backend = backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV);
  if (!backend) return caseError('Service not configured', 503);

  try {
    const session = await auth0.getSession();
    if (!session) return caseError('Authentication required', 401);

    let token: string;
    try {
      const accessToken = await auth0.getAccessToken();
      if (!accessToken.token) return caseError('Authentication needs renewal', 401);
      token = accessToken.token;
    } catch {
      return caseError('Authentication needs renewal', 401);
    }

    // Forward the Vercel-injected project identity only to the dedicated Preview API.
    // Vercel validates its signature and the Preview-to-Preview trusted-source rule.
    let previewOidc: string | null = null;
    if (process.env.VERCEL_ENV === 'preview' && backend === 'https://practicamia-api-git-preview-auth-rev-599637-firatadembilge-4729.vercel.app') {
      previewOidc = (await requestHeaders()).get('x-vercel-oidc-token');
      if (!previewOidc) return caseError('Preview service identity unavailable', 503);
    }
    const response = await fetch(backend + path, {
      method,
      headers: {
        Authorization: 'Bearer ' + token,
        ...(previewOidc ? { 'x-vercel-trusted-oidc-idp-token': previewOidc } : {}),
        ...(payload !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(payload !== undefined ? { body: JSON.stringify(payload) } : {}),
      redirect: 'manual',
      cache: 'no-store',
      signal: AbortSignal.timeout(timeoutMs),
    });
    return new NextResponse(response.status === 204 ? null : await response.text(), {
      status: response.status,
      headers: { ...headers, 'Content-Type': 'application/json' },
    });
  } catch {
    return caseError('Backend unavailable', 502);
  }
}
