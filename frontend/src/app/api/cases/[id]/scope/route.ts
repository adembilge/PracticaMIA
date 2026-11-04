import { NextRequest } from 'next/server';
import { isCaseId, isScopePayload } from '@/lib/case-scope.js';
import { caseError, proxyCaseRequest, rejectCrossOrigin } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';
type Context = { params: Promise<{ id: string }> };

export async function PATCH(request: NextRequest, { params }: Context) {
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  const { id } = await params;
  if (!isCaseId(id)) return caseError('Case not found', 404);

  const length = Number(request.headers.get('content-length') || '0');
  if (length > 2048) return caseError('Payload too large', 413);
  const payload: unknown = await request.json().catch(() => null);
  if (!isScopePayload(payload)) return caseError('Invalid scope answers', 422);
  return proxyCaseRequest('PATCH', '/api/v1/cases/' + id + '/scope', payload);
}
