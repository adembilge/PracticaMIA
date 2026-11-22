import { reviewerPreviewEnabled } from '@/lib/reviewer-preview.js';
import { isCaseId } from '@/lib/case-scope.js';
import { backendError, proxyAuthenticatedRequest } from '@/lib/backend-proxy';

export const dynamic = 'force-dynamic';

type Context = { params: Promise<{ id: string }> };

export async function GET(_request: Request, { params }: Context) {
  if (!reviewerPreviewEnabled(process.env)) return backendError('Not found', 404);
  const { id } = await params;
  if (!isCaseId(id)) return backendError('Version not found', 404);
  return proxyAuthenticatedRequest(
    'GET', '/api/v1/knowledge/review/versions/' + id,
  );
}
