import { NextRequest } from 'next/server';
import { isUuid } from '@/lib/task-scope.js';
import { isIndividualPdfReviewPayload, reviewerPreviewEnabled } from '@/lib/reviewer-preview.js';
import { backendError, proxyAuthenticatedRequest, rejectCrossOrigin } from '@/lib/backend-proxy';

export const dynamic = 'force-dynamic';
type Context = { params: Promise<{ id: string }> };

/** The backend binds identity to a verified reviewer JWT and records audit events. */
export async function POST(request: NextRequest, { params }: Context) {
  if (!reviewerPreviewEnabled(process.env)) return backendError('Not found', 404);
  const { id } = await params;
  if (!isUuid(id)) return backendError('Version not found', 404);
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  if (Number(request.headers.get('content-length') || '0') > 2000) {
    return backendError('Payload too large', 413);
  }
  const body: unknown = await request.json().catch(() => null);
  if (!isIndividualPdfReviewPayload(body)) {
    return backendError('Invalid individual source-review decision', 422);
  }
  // Do not forward browser-asserted reviewer identity, source status or permissions.
  const reviewed = body as { expected_sha256: string; review_note: string };
  return proxyAuthenticatedRequest('POST',
    '/api/v1/knowledge/review/versions/' + id + '/approve', {
      expected_sha256: reviewed.expected_sha256,
      review_note: reviewed.review_note.trim(),
    }, 15000);
}
