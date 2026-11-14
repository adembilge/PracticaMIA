import { notFound } from 'next/navigation';
import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { isCaseId } from '@/lib/case-scope.js';
import { privateDocumentsUiEnabled } from '@/lib/private-documents.js';
import { PrivateDocumentsWorkspace } from '@/components/PrivateDocumentsWorkspace';

export const dynamic = 'force-dynamic';

export default async function PrivateDocumentsPage({
  params,
}: {params: Promise<{ id: string }>}) {
  if (!privateDocumentsUiEnabled(process.env)) notFound();
  const {id} = await params;
  if (!isCaseId(id)) notFound();
  const session = auth0 ? await auth0.getSession() : null;
  return <PrivateDocumentsWorkspace
    caseId={id}
    signedIn={Boolean(session)}
    configured={Boolean(auth0 && backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
  />;
}
