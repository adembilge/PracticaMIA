import {NextRequest, NextResponse} from 'next/server';
import {sameOrigin} from '@/lib/auth-configuration.js';
import {caseError, proxyCaseRequest} from '@/lib/case-proxy';
import {isCaseId} from '@/lib/case-scope.js';
import {publicSyntheticAIEnabled} from '@/lib/public-synthetic-ai.js';
import {
  validateCaseGuidanceRequest, parseStoredCase,
  getCaseGuidancePlan, makeCaseGuidanceMessages,
} from '@/lib/case-guidance.js';

export const dynamic = 'force-dynamic';

type Context = {params: Promise<{id: string}>};

function response(body: object, status = 200) {
  return NextResponse.json(body, {
    status,
    headers: {'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff'},
  });
}

function limitedModelText(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const text = value.trim();
  // The authoritative product action is always computed locally from saved answers.
  // Suppress obvious new administrative instructions emitted by a free model.
  if (text.length < 8 || text.length > 650 || /https?:\/\//i.test(text) ||
      /[\r\n{}]/.test(text) ||
      /(?:utility bill|landlord declaration|signed lease|identity document|passport|permesso|bolletta|passaporto|documenti obbligatori|mandatory documents|review queue|coda di revisione|eligible|idoneo|approvata|accepted by the municipality)/i.test(text)) return null;
  return text;
}

export async function POST(request: NextRequest, context: Context) {
  if (!publicSyntheticAIEnabled(process.env)) return caseError('Not found', 404);
  if (!sameOrigin(request.url, request.headers.get('origin'))) {
    return caseError('Forbidden origin', 403);
  }
  const {id} = await context.params;
  if (!isCaseId(id)) return caseError('Case not found', 404);
  if (!request.headers.get('content-type')?.startsWith('application/json')) {
    return caseError('Invalid content type', 415);
  }
  const declared = Number(request.headers.get('content-length') ?? '0');
  if (!Number.isSafeInteger(declared) || declared < 1 || declared > 256) {
    return caseError('Invalid request size', 413);
  }
  const body: unknown = await request.json().catch(() => null);
  const input = validateCaseGuidanceRequest(body);
  if (!input) return caseError('Invalid guidance request', 422);

  // Source of truth is the owner-scoped case backend, NEVER client-provided
  // answers, an untrusted chat prompt, or the static fictional example.
  const upstream = await proxyCaseRequest('GET', '/api/v1/cases/' + id);
  if (upstream.status !== 200) {
    if (upstream.status === 401) return caseError('Sign-in required', 401);
    if (upstream.status === 404) return caseError('Case not found', 404);
    return caseError('Case service unavailable', 502);
  }
  let raw: unknown;
  try { raw = await upstream.json(); } catch {
    return caseError('Case data unavailable', 502);
  }
  const saved = parseStoredCase(raw, id);
  if (!saved) return caseError('Saved case could not be verified', 502);
  const guidance = getCaseGuidancePlan(saved, input.language);
  if (!guidance) return caseError('Guidance unavailable', 503);

  const messages = makeCaseGuidanceMessages(guidance, input);
  if (!messages) return caseError('Guidance unavailable', 503);
  let modelExplanation: string | null = null;
  try {
    const provider = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type':'application/json',
        Authorization: 'Bearer ' + process.env.OPENROUTER_API_KEY,
        'HTTP-Referer': 'https://practicamia.vercel.app',
        'X-Title': 'PracticaMIA saved-case workflow explainer',
      },
      body: JSON.stringify({
        model:'openrouter/free', messages, max_tokens:220,
        temperature:0.1, reasoning:{effort:'none'},
      }),
      cache:'no-store',
      redirect:'error',
      signal:AbortSignal.timeout(18000),
    });
    if (provider.ok) {
      const data: unknown = await provider.json();
      const answer = (data as {choices?: {message?: {content?: unknown}}[]})
        ?.choices?.[0]?.message?.content;
      modelExplanation = limitedModelText(answer);
    }
  } catch {
    // Deterministic case-specific next steps remain available when AI fails.
  }
  return response({
    guidance,
    ai_explanation: modelExplanation,
    ai_available: modelExplanation !== null,
    source_of_truth: 'saved_authenticated_case',
    sent_to_model: 'abstract_product_status_and_question_number_only',
    not_an_eligibility_decision: true,
    not_a_document_checklist: true,
    not_a_submission: true,
  });
}
