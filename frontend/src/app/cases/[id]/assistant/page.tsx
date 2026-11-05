import { notFound } from 'next/navigation';
import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { assistantPreviewEnabled } from '@/lib/assistant-preview.js';
import { isCaseId } from '@/lib/case-scope.js';
import { AssistantPreview } from '@/components/AssistantPreview';

export const dynamic = 'force-dynamic';

export default async function AssistantPreviewPage({
  params,
}: { params: Promise<{ id: string }> }) {
  if (!assistantPreviewEnabled(process.env)) notFound();
  const { id } = await params;
  if (!isCaseId(id)) notFound();
  const session = auth0 ? await auth0.getSession() : null;
  return <AssistantPreview
    caseId={id}
    configured={Boolean(auth0 && backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
    signedIn={Boolean(session)}
  />;
}
