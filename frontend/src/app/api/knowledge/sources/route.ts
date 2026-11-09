import { proxyCaseRequest } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';

/** Read-only, authenticated source registry; user tokens stay server-side. */
export async function GET() {
  return proxyCaseRequest('GET', '/api/v1/knowledge/sources');
}
