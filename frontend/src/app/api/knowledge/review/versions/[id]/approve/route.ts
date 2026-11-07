import { NextRequest } from 'next/server';
import { isCaseId } from '@/lib/case-scope.js';
import { isIndividualPdfReviewPayload, reviewerPreviewEnabled } from '@/lib/reviewer-preview.js';
import { caseError, proxyCaseRequest, rejectCrossOrigin } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';
type Context = { params: Promise<{ id: string }> };

/** The backend binds identity to a verified reviewer JWT and records audit events. */
export async function POST(request: NextRequest, { params }: Context) {
  if (!reviewerPreviewEnabled(process.env)) return caseError('Not found', 404);
  const { id } = await params;
  if (!isCaseId(id)) return caseError('Version not found', 404);
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  if (Number(request.headers.get('content-length') || '0') > 2000) {
    return caseError('Payload too large', 413);
  }
  const body: unknown = await request.json().catch(() => null);
  if (!isIndividualPdfReviewPayload(body)) {
    return caseError('Invalid individual source-review decision', 422);
  }
  // Do not forward browser-asserted reviewer identity, source status or permissions.
  const reviewed = body as { expected_sha256: string; review_note: string };
  return proxyCaseRequest('POST',
    '/api/v1/knowledge/review/versions/' + id + '/approve', {
      expected_sha256: reviewed.expected_sha256,
      review_note: reviewed.review_note.trim(),
    }, 15000);
}
