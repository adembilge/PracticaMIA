import { NextRequest, NextResponse } from 'next/server';
import { auth0 } from '@/lib/auth0';
import { backendOrigin, sameOrigin } from '@/lib/auth-configuration.js';

export const dynamic = 'force-dynamic';

const noStore = { 'Cache-Control': 'no-store' };
const unavailable = () => NextResponse.json({ error: 'Service not configured' }, { status: 503, headers: noStore });

async function authorizedBackend() {
  if (!auth0) return { error: unavailable() } as const;
  const session = await auth0.getSession();
  if (!session) return {
    error: NextResponse.json({ error: 'Authentication required' }, { status: 401, headers: noStore }),
  } as const;
  const origin = backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV);
  if (!origin) return { error: unavailable() } as const;
  try {
    const { token } = await auth0.getAccessToken();
    if (!token) throw new Error('No access token');
    return { origin, token } as const;
  } catch {
    return {
      error: NextResponse.json({ error: 'Authentication needs renewal' }, { status: 401, headers: noStore }),
    } as const;
  }
}

async function forward(method: 'GET' | 'POST') {
  const authorization = await authorizedBackend();
  if ('error' in authorization) return authorization.error;
  try {
    const response = await fetch(authorization.origin + '/api/v1/cases', {
      method,
      headers: {
        Authorization: 'Bearer ' + authorization.token,
        ...(method === 'POST' ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(method === 'POST' ? { body: '{}' } : {}),
      cache: 'no-store',
      signal: AbortSignal.timeout(8000),
    });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { 'Content-Type': 'application/json', ...noStore },
    });
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502, headers: noStore });
  }
}

export async function GET() {
  return forward('GET');
}

export async function POST(request: NextRequest) {
  if (!sameOrigin(request.url, request.headers.get('origin'))) {
    return NextResponse.json({ error: 'Forbidden origin' }, { status: 403, headers: noStore });
  }
  // Never forward arbitrary client-supplied personal data.
  return forward('POST');
}
