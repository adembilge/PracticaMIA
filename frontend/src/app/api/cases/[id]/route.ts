import { NextRequest } from 'next/server';
import { isCaseId } from '@/lib/case-scope.js';
import { caseError, proxyCaseRequest, rejectCrossOrigin } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';
type Context = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, { params }: Context) {
  const { id } = await params;
  if (!isCaseId(id)) return caseError('Case not found', 404);
  return proxyCaseRequest('GET', '/api/v1/cases/' + id);
}

export async function DELETE(request: NextRequest, { params }: Context) {
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  const { id } = await params;
  if (!isCaseId(id)) return caseError('Case not found', 404);
  return proxyCaseRequest('DELETE', '/api/v1/cases/' + id);
}
