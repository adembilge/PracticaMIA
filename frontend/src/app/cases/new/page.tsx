import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { syntheticDemoAvailable } from '@/lib/synthetic-demo-guard.js';
import { StartCaseView } from '@/components/StartCaseView';

export const dynamic = 'force-dynamic';

export default async function NewCasePage() {
  const session = auth0 ? await auth0.getSession() : null;
  return <StartCaseView
    signedIn={Boolean(session)}
    canSave={Boolean(auth0 && backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
    canExplore={syntheticDemoAvailable(process.env)}
  />;
}
