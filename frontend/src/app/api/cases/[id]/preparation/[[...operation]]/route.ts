import { NextRequest } from 'next/server';
import { isCaseId } from '@/lib/case-scope.js';
import { caseError, proxyCaseRequest, proxySyntheticDocumentUpload, rejectCrossOrigin } from '@/lib/case-proxy';
import { preparationPreviewEnabled, isPreparationPayload } from '@/lib/preparation-preview.js';

export const dynamic = 'force-dynamic';
type Context = { params: Promise<{ id: string; operation?: string[] }> };

function routeFor(id: string, operation: string[], method: string) {
  const path = '/api/v1/cases/' + id + '/preparation';
  const action = operation.join('/');
  if (method === 'GET' && ['', 'checklist', 'documents', 'package', 'handoff', 'reference-evidence', 'anpr-draft'].includes(action)) {
    return { path: path + (action ? '/' + action : ''), action };
  }
  if (method === 'PUT' && action === 'facts') return { path: path + '/facts', action };
  if (method === 'POST' && (action === 'documents' || action === 'package/approve' || action === 'guide')) {
    return { path: path + '/' + action, action };
  }
  const match = action.match(/^documents\/([0-9a-fA-F-]{36})(?:\/(extract|review|confirm-fields))?$/);
  if (match && isCaseId(match[1])) {
    if (method === 'POST' && match[2]) {
      return { path: path + '/documents/' + match[1] + '/' + match[2],
               action: 'document/' + match[2] };
    }
    if (method === 'DELETE' && !match[2]) {
      return { path: path + '/documents/' + match[1], action: 'document/delete' };
    }
  }
  return null;
}

async function handle(request: NextRequest, context: Context, method: string) {
  if (!preparationPreviewEnabled(process.env)) return caseError('Not found', 404);
  const { id, operation = [] } = await context.params;
  if (!isCaseId(id) || operation.length > 3 ||
      operation.some(x => !/^[a-zA-Z0-9-]{1,64}$/.test(x))) {
    return caseError('Case not found', 404);
  }
  const route = routeFor(id, operation, method);
  if (!route) return caseError('Not found', 404);
  if (method !== 'GET') {
    const originError = rejectCrossOrigin(request);
    if (originError) return originError;
  }
  if (method === 'GET' || method === 'DELETE') {
    return proxyCaseRequest(method, route.path);
  }
  if (route.action === 'document/extract') {
    return proxyCaseRequest('POST', route.path);
  }
  const declaredLength = Number(request.headers.get('content-length'));
  if (!Number.isFinite(declaredLength) || declaredLength < 1 ||
      declaredLength > (route.action === 'documents' ? 2 * 1024 * 1024 + 16384 : 4096)) {
    return caseError('Payload too large or missing length', 413);
  }
  if (route.action === 'documents') {
    if (!request.headers.get('content-type')?.startsWith('multipart/form-data;')) {
      return caseError('Invalid upload type', 415);
    }
    const form = await request.formData().catch(() => null);
    const file = form?.get('file');
    const documentType = form?.get('document_type');
    if (!(file instanceof File) || file.size < 1 || file.size > 2 * 1024 * 1024 ||
        typeof documentType !== 'string' ||
        !/^[a-z][a-z0-9_]{0,63}$/.test(documentType)) {
      return caseError('Unsupported synthetic document', 422);
    }
    const safe = new FormData();
    safe.set('file', file, 'synthetic-upload');
    safe.set('document_type', documentType);
    return proxySyntheticDocumentUpload(route.path, safe);
  }
  const raw = await request.text().catch(() => '');
  if (raw.length > 4096 || !request.headers.get('content-type')?.startsWith('application/json')) {
    return caseError('Invalid payload', 422);
  }
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return caseError('Invalid payload', 422);
  }
  if (!isPreparationPayload(route.action, data)) return caseError('Invalid payload', 422);
  return proxyCaseRequest(method as 'POST' | 'PUT', route.path, data);
}

export async function GET(request: NextRequest, context: Context) {
  return handle(request, context, 'GET');
}
export async function POST(request: NextRequest, context: Context) {
  return handle(request, context, 'POST');
}
export async function PUT(request: NextRequest, context: Context) {
  return handle(request, context, 'PUT');
}
export async function DELETE(request: NextRequest, context: Context) {
  return handle(request, context, 'DELETE');
}
