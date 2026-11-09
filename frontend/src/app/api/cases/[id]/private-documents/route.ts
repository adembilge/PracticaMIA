import { NextRequest } from 'next/server';
import { isCaseId } from '@/lib/case-scope.js';
import { caseError, proxyCaseRequest, proxyPrivateDocumentUpload } from '@/lib/case-proxy';
import {
  PRIVATE_DOCUMENT_MAX_BYTES, privateDocumentsUiEnabled, isPrivateUploadMeta,
} from '@/lib/private-documents.js';

export const dynamic = 'force-dynamic';
type Context = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, {params}: Context) {
  if (!privateDocumentsUiEnabled(process.env)) return caseError('Not found', 404);
  const {id} = await params;
  if (!isCaseId(id)) return caseError('Case not found', 404);
  return proxyCaseRequest('GET', '/api/v1/cases/' + id + '/private-documents');
}

export async function POST(request: NextRequest, {params}: Context) {
  if (!privateDocumentsUiEnabled(process.env)) return caseError('Not found', 404);
  const {id} = await params;
  if (!isCaseId(id)) return caseError('Case not found', 404);
  // Strict origin check: missing origin is rejected for multipart writes.
  if (request.headers.get('origin') !== new URL(request.url).origin) {
    return caseError('Forbidden origin', 403);
  }
  const bytes = Number(request.headers.get('content-length') || '0');
  if (!Number.isSafeInteger(bytes) || bytes < 1 || bytes > PRIVATE_DOCUMENT_MAX_BYTES + 16384) {
    return caseError('Upload too large or missing content length', 413);
  }
  if (!request.headers.get('content-type')?.startsWith('multipart/form-data;')) {
    return caseError('Unsupported content type', 415);
  }
  const input = await request.formData().catch(() => null);
  const file = input?.get('file');
  const category = input?.get('category');
  const ack = input?.get('privacy_ack');
  const version = input?.get('consent_version');
  if (!(file instanceof File) ||
      typeof category !== 'string' || typeof ack !== 'string' ||
      typeof version !== 'string' ||
      !isPrivateUploadMeta(category, ack, version, file.size, file.type)) {
    return caseError('Unsupported upload or missing privacy acknowledgement', 422);
  }
  const safe = new FormData();
  safe.set('file', file, 'document');
  safe.set('category', category);
  safe.set('privacy_ack', ack);
  safe.set('consent_version', version);
  return proxyPrivateDocumentUpload('/api/v1/cases/' + id + '/private-documents', safe);
}
