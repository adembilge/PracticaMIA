import { NextRequest } from 'next/server';
import { isCaseId } from '@/lib/case-scope.js';
import { caseError, proxyCaseRequest, rejectCrossOrigin } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';

export async function PATCH(request: NextRequest, {params}: {params: Promise<{id: string}>}) {
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  const {id} = await params;
  if (!isCaseId(id)) return caseError('Case not found', 404);
  if (!request.headers.get('content-type')?.startsWith('application/json')) {
    return caseError('Invalid content type', 415);
  }
  const length = Number(request.headers.get('content-length'));
  if (!Number.isSafeInteger(length) || length < 1 || length > 64) {
    return caseError('Invalid request size', 413);
  }
  const raw = await request.text();
  if (raw.length > 64) return caseError('Request too large', 413);
  let payload: unknown;
  try { payload = JSON.parse(raw); }
  catch { return caseError('Invalid archive request', 422); }
  if (!payload || typeof payload !== 'object' || Object.keys(payload).length !== 1 ||
      !('archived' in payload) || typeof payload.archived !== 'boolean') {
    return caseError('Invalid archive request', 422);
  }
  return proxyCaseRequest('PATCH', '/api/v1/cases/' + id + '/archive', {archived: payload.archived});
}
