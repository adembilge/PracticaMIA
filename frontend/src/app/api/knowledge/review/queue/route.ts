import { reviewerPreviewEnabled } from '@/lib/reviewer-preview.js';
import { backendError, proxyAuthenticatedRequest } from '@/lib/backend-proxy';

export const dynamic = 'force-dynamic';

/** Auth0 reviewer-only queue, including PDF snapshots excluded from browser queue. */
export async function GET() {
  if (!reviewerPreviewEnabled(process.env)) return backendError('Not found', 404);
  return proxyAuthenticatedRequest('GET', '/api/v1/knowledge/review/queue');
}
