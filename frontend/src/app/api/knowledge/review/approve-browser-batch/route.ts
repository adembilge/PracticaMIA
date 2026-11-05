import { NextRequest } from 'next/server';
import {
  isBrowserReviewBatchPayload, reviewerPreviewEnabled,
} from '@/lib/reviewer-preview.js';
import { caseError, proxyCaseRequest, rejectCrossOrigin } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  if (!reviewerPreviewEnabled(process.env)) return caseError('Not found', 404);
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  if (Number(request.headers.get('content-length') || '0') > 10000) {
    return caseError('Payload too large', 413);
  }
  const body: unknown = await request.json().catch(() => null);
  if (!isBrowserReviewBatchPayload(body)) {
    return caseError('Invalid review decision', 422);
  }
  return proxyCaseRequest(
    'POST', '/api/v1/knowledge/review/approve-browser-batch', body, 15000,
  );
}
