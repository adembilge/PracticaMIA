import { NextRequest } from 'next/server';
import { caseError, proxyCaseRequest, rejectCrossOrigin } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const view = request.nextUrl.searchParams.get('view') ?? 'active';
  if (view !== 'active' && view !== 'archived') return caseError('Unknown case view', 400);
  return proxyCaseRequest('GET', '/api/v1/cases?view=' + view);
}

export async function POST(request: NextRequest) {
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  // Never forward arbitrary browser-supplied personal data.
  return proxyCaseRequest('POST', '/api/v1/cases', {});
}
