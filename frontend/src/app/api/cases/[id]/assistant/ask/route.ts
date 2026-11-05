import { NextRequest } from 'next/server';
import { assistantPreviewEnabled, isAssistantQuestionPayload } from '@/lib/assistant-preview.js';
import { isCaseId } from '@/lib/case-scope.js';
import { caseError, proxyCaseRequest, rejectCrossOrigin } from '@/lib/case-proxy';

export const dynamic = 'force-dynamic';
type Context = { params: Promise<{ id: string }> };

export async function POST(request: NextRequest, { params }: Context) {
  if (!assistantPreviewEnabled(process.env)) return caseError('Not found', 404);
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;

  const { id } = await params;
  if (!isCaseId(id)) return caseError('Case not found', 404);
  const length = Number(request.headers.get('content-length') || '0');
  if (length > 1024) return caseError('Payload too large', 413);
  const payload: unknown = await request.json().catch(() => null);
  if (!isAssistantQuestionPayload(payload)) return caseError('Invalid preview question', 422);
  return proxyCaseRequest(
    'POST', '/api/v1/cases/' + id + '/assistant/ask', payload, 20000,
  );
}
