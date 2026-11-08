import { NextRequest, NextResponse } from 'next/server';
import { auth0 } from '@/lib/auth0';
import { sameOrigin } from '@/lib/auth-configuration.js';
import {
  publicSyntheticAIEnabled, syntheticAIMessages,
} from '@/lib/public-synthetic-ai.js';

export const dynamic = 'force-dynamic';

function json(body: object, status: number) {
  return NextResponse.json(body, {
    status,
    headers: {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'},
  });
}

export async function POST(request: NextRequest) {
  // Explicitly limited to an authenticated, fictional Production demonstration.
  if (!publicSyntheticAIEnabled(process.env)) return json({error: 'Not found'}, 404);
  if (!sameOrigin(request.url, request.headers.get('origin'))) {
    return json({error: 'Not allowed'}, 403);
  }
  if (!auth0) return json({error: 'Sign-in unavailable'}, 503);
  const session = await auth0.getSession().catch(() => null);
  if (!session?.user?.sub) return json({error: 'Sign-in required'}, 401);

  if (!request.headers.get('content-type')?.startsWith('application/json')) {
    return json({error: 'Invalid content type'}, 415);
  }
  const size = Number(request.headers.get('content-length') || '0');
  if (!Number.isFinite(size) || size > 512) return json({error: 'Invalid request size'}, 413);
  const body: unknown = await request.json().catch(() => null);
  const messages = syntheticAIMessages(body);
  if (!messages) return json({error: 'Invalid synthetic topic'}, 422);

  // Only fixed fictional example prompts leave this backend.
  // The browser cannot submit arbitrary text, case values, or documents.
  try {
    const result = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.OPENROUTER_API_KEY}`,
        'HTTP-Referer': 'https://practicamia.vercel.app',
        'X-Title': 'PracticaMIA fictional demonstration',
      },
      body: JSON.stringify({
        model: 'openrouter/free',
        messages,
        max_tokens: 180,
        temperature: 0.2,
      }),
      cache: 'no-store',
      signal: AbortSignal.timeout(16000),
    });
    if (!result.ok) return json({error: 'Free AI provider is temporarily unavailable'}, 503);
    const data: unknown = await result.json();
    const reply = (data as {choices?: {message?: {content?: unknown}}[]})
      ?.choices?.[0]?.message?.content;
    if (typeof reply !== 'string' || !reply.trim()) {
      return json({error: 'No AI response available'}, 503);
    }
    return json({
      status: 'generated',
      response: reply.trim().slice(0, 1500),
      model_route: 'openrouter/free',
      synthetic_only: true,
      disclaimer: 'Fictional example only. Not verified administrative guidance.',
    }, 200);
  } catch {
    // Never return the provider's raw body, headers or credential to clients.
    return json({error: 'Free AI provider is temporarily unavailable'}, 503);
  }
}
