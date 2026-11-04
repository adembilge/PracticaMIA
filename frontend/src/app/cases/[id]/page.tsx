import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { SavedCaseWorkspace } from '@/components/SavedCaseWorkspace';

export const dynamic = 'force-dynamic';

export default async function SavedCasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = auth0 ? await auth0.getSession() : null;
  return <SavedCaseWorkspace
    caseId={id}
    signedIn={Boolean(session)}
    configured={Boolean(auth0 && backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
  />;
}
