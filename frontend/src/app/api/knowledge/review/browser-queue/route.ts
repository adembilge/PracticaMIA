import { reviewerPreviewEnabled } from '@/lib/reviewer-preview.js';
import { caseError, proxyCaseRequest } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';

export async function GET() {
  if (!reviewerPreviewEnabled(process.env)) return caseError('Not found', 404);
  return proxyCaseRequest('GET', '/api/v1/knowledge/review/browser-queue');
}
