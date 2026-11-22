import { NextRequest } from 'next/server';
import {
  isBrowserReviewBatchPayload, reviewerPreviewEnabled,
} from '@/lib/reviewer-preview.js';
import { backendError, proxyAuthenticatedRequest, rejectCrossOrigin } from '@/lib/backend-proxy';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  if (!reviewerPreviewEnabled(process.env)) return backendError('Not found', 404);
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  if (Number(request.headers.get('content-length') || '0') > 10000) {
    return backendError('Payload too large', 413);
  }
  const body: unknown = await request.json().catch(() => null);
  if (!isBrowserReviewBatchPayload(body)) {
    return backendError('Invalid review decision', 422);
  }
  return proxyAuthenticatedRequest(
    'POST', '/api/v1/knowledge/review/approve-browser-batch', body, 15000,
  );
}
