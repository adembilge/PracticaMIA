import { NextRequest } from 'next/server';
import { isCaseId } from '@/lib/case-scope.js';
import { caseError, proxyCaseRequest } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';
type Context = { params: Promise<{ id: string }> };

/** User account ownership and signed rule evaluation are enforced in the API.
 * This server-side Auth0 proxy never accepts client-authored case facts.
 */
export async function GET(_request: NextRequest, { params }: Context) {
  const {id} = await params;
  if (!isCaseId(id)) return caseError('Case not found', 404);
  return proxyCaseRequest('GET', '/api/v1/cases/' + id + '/checklist', undefined, 20000);
}
