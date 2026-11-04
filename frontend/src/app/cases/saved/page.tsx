import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { SavedCasesView } from '@/components/SavedCasesView';

export const dynamic = 'force-dynamic';

export default async function SavedCasesPage() {
  const session = auth0 ? await auth0.getSession() : null;
  return (
    <SavedCasesView
      configured={Boolean(auth0)}
      signedIn={Boolean(session)}
      backendConfigured={Boolean(backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
    />
  );
}
