import { notFound } from 'next/navigation';
import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { isCaseId } from '@/lib/case-scope.js';
import { preparationPreviewEnabled } from '@/lib/preparation-preview.js';
import { PreparationPreview } from '@/components/PreparationPreview';

export const dynamic = 'force-dynamic';

export default async function PreparationPage({
  params,
}: { params: Promise<{ id: string }> }) {
  if (!preparationPreviewEnabled(process.env)) notFound();
  const { id } = await params;
  if (!isCaseId(id)) notFound();
  const session = auth0 ? await auth0.getSession() : null;
  return <PreparationPreview
    caseId={id}
    configured={Boolean(auth0 && backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
    signedIn={Boolean(session)}
  />;
}
