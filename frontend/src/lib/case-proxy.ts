import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { auth0 } from '@/lib/auth0';
import { backendOrigin, sameOrigin } from '@/lib/auth-configuration.js';

const headers = { 'Cache-Control': 'private, no-store' };
type CaseMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

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

    const response = await fetch(backend + path, {
      method,
      headers: {
        Authorization: 'Bearer ' + token,
        ...(payload !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(payload !== undefined ? { body: JSON.stringify(payload) } : {}),
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


/** Only the disabled-by-default synthetic preview uses a multipart forwarder. */
export async function proxySyntheticDocumentUpload(path: string, form: FormData) {
  if (!auth0) return caseError('Service not configured', 503);
  const backend = backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV);
  if (!backend) return caseError('Service not configured', 503);
  try {
    const session = await auth0.getSession();
    if (!session) return caseError('Authentication required', 401);
    const credential = await auth0.getAccessToken();
    if (!credential.token) return caseError('Authentication needs renewal', 401);
    const response = await fetch(backend + path, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + credential.token,
        'X-PracticaMIA-Synthetic-Only': 'YES',
      },
      body: form,
      cache: 'no-store',
      signal: AbortSignal.timeout(20000),
    });
    return new NextResponse(response.status === 204 ? null : await response.text(), {
      status: response.status,
      headers: { ...headers, 'Content-Type': 'application/json' },
    });
  } catch {
    return caseError('Backend unavailable', 502);
  }
}
