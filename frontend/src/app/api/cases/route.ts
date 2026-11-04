import { NextRequest } from 'next/server';
import { proxyCaseRequest, rejectCrossOrigin } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';

export async function GET() {
  return proxyCaseRequest('GET', '/api/v1/cases');
}

export async function POST(request: NextRequest) {
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  // Never forward arbitrary browser-supplied personal data.
  return proxyCaseRequest('POST', '/api/v1/cases', {});
}
