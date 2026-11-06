import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { assistantPreviewEnabled } from '@/lib/assistant-preview.js';
import { preparationPreviewEnabled } from '@/lib/preparation-preview.js';
import { SavedCaseWorkspace } from '@/components/SavedCaseWorkspace';

export const dynamic = 'force-dynamic';

export default async function SavedCasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = auth0 ? await auth0.getSession() : null;
  return <SavedCaseWorkspace
    caseId={id}
    signedIn={Boolean(session)}
    assistantEnabled={assistantPreviewEnabled(process.env)}
    preparationEnabled={preparationPreviewEnabled(process.env)}
    configured={Boolean(auth0 && backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
  />;
}
