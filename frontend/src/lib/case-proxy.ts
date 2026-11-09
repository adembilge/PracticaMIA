import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { headers as requestHeaders } from 'next/headers';
import { auth0 } from '@/lib/auth0';
import { backendOrigin, sameOrigin } from '@/lib/auth-configuration.js';

const headers = { 'Cache-Control': 'private, no-store' };
type CaseMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/** Restrict project identity forwarding to the dedicated protected Preview API. */
async function previewIdentity(backend: string): Promise<string | null> {
  if (process.env.VERCEL_ENV !== 'preview' || backend !== 'https://practicamia-api-git-preview-auth-rev-599637-firatadembilge-4729.vercel.app') return null;
  const oidc = (await requestHeaders()).get('x-vercel-oidc-token');
  if (!oidc) throw new Error('Preview service identity unavailable');
  return oidc;
}

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

    const previewOidc = await previewIdentity(backend);
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
    const previewOidc = await previewIdentity(backend);
    const response = await fetch(backend + path, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + credential.token,
        ...(previewOidc ? { 'x-vercel-trusted-oidc-idp-token': previewOidc } : {}),
        'X-PracticaMIA-Synthetic-Only': 'YES',
      },
      body: form,
      redirect: 'manual',
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

/** Strictly separated from synthetic Preview uploads; never forwards file names to AI. */
export async function proxyPrivateDocumentUpload(path: string, form: FormData) {
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
      headers: { Authorization: 'Bearer ' + credential.token },
      body: form,
      redirect: 'manual',
      cache: 'no-store',
      signal: AbortSignal.timeout(25000),
    });
    return new NextResponse(response.status === 204 ? null : await response.text(), {
      status: response.status,
      headers: { ...headers, 'Content-Type': 'application/json' },
    });
  } catch {
    return caseError('Private document service unavailable', 502);
  }
}


/** Authenticated, no-store binary PDF proxy. Never send Auth0 access tokens
 * to the browser or trust an upstream Content-Disposition filename.
 */
export async function proxyCasePdf(path: string) {
  if (!auth0) return caseError('Service not configured', 503);
  const backend = backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV);
  if (!backend) return caseError('Service not configured', 503);
  try {
    if (!await auth0.getSession()) return caseError('Authentication required', 401);
    const credential = await auth0.getAccessToken();
    if (!credential.token) return caseError('Authentication needs renewal', 401);
    const previewOidc = await previewIdentity(backend);
    const upstream = await fetch(backend + path, {
      method: 'GET',
      headers: {
        Authorization: 'Bearer ' + credential.token,
        ...(previewOidc ? { 'x-vercel-trusted-oidc-idp-token': previewOidc } : {}),
        Accept: 'application/pdf',
      },
      cache: 'no-store', redirect: 'manual',
      signal: AbortSignal.timeout(20000),
    });
    if (!upstream.ok) {
      const status = [401, 403, 404, 409, 503].includes(upstream.status)
        ? upstream.status : 502;
      return caseError(
        status === 409 ? 'Package blocked: resolve case or document issues'
          : 'Preparation package unavailable', status,
      );
    }
    const media = upstream.headers.get('content-type')?.split(';')[0].trim();
    const declared = Number(upstream.headers.get('content-length') ?? '0');
    if (media !== 'application/pdf' || !Number.isFinite(declared)
        || declared > 1_000_000) return caseError('Invalid document response', 502);
    const binary = await upstream.arrayBuffer();
    const bytes = new Uint8Array(binary);
    if (bytes.byteLength < 30 || bytes.byteLength > 1_000_000 ||
        String.fromCharCode(...bytes.subarray(0, 5)) !== '%PDF-') {
      return caseError('Invalid document response', 502);
    }
    return new NextResponse(bytes, {
      status: 200,
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="practicamia-preparation-draft.pdf"',
        'Content-Length': String(bytes.byteLength),
        'Cache-Control': 'private, no-store',
        'X-Content-Type-Options': 'nosniff',
        'X-Robots-Tag': 'noindex',
        'Referrer-Policy': 'no-referrer',
        'Content-Security-Policy': "default-src 'none'; sandbox",
      },
    });
  } catch {
    return caseError('Preparation package service unavailable', 502);
  }
}
