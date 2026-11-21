import {NextRequest} from 'next/server';
import {caseError, proxyCaseRequest, rejectCrossOrigin} from '@/lib/case-proxy';
import {singleChatPreviewEnabled, allowedChatPath, allowedChatQuery} from '@/lib/single-chat-preview.js';

export const dynamic = 'force-dynamic';
type Context = {params: Promise<{path: string[]}>};

function endpoint(path: string[], method: 'GET' | 'POST', request: NextRequest): string | null {
  // Input is an untrusted URL. Only the intentionally exposed conversation APIs pass.
  const value = path.join('/');
  if (!allowedChatPath(method, value)) return null;
  if (!allowedChatQuery(value, request.nextUrl.searchParams)) return null;
  return '/api/v1/agent/' + value + request.nextUrl.search;
}

export async function GET(request: NextRequest, {params}: Context) {
  if (!singleChatPreviewEnabled(process.env)) return caseError('Not found', 404);
  const target = endpoint((await params).path, 'GET', request);
  return target ? proxyCaseRequest('GET', target, undefined, 12000)
    : caseError('Not found', 404);
}

export async function POST(request: NextRequest, {params}: Context) {
  if (!singleChatPreviewEnabled(process.env)) return caseError('Not found', 404);
  const error = rejectCrossOrigin(request);
  if (error) return error;
  const target = endpoint((await params).path, 'POST', request);
  if (!target) return caseError('Not found', 404);
  if (!request.headers.get('content-type')?.startsWith('application/json')) {
    return caseError('Expected JSON payload', 415);
  }
  const raw = await request.text();
  if (raw.length > 16000) return caseError('Payload too large', 413);
  let body: unknown;
  try {
    body = JSON.parse(raw);
  } catch {
    return caseError('Invalid JSON', 400);
  }
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return caseError('Invalid payload', 400);
  }
  return proxyCaseRequest('POST', target, body, 12000);
}
