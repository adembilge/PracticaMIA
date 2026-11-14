import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { syntheticDemoAvailable } from '@/lib/synthetic-demo-guard.js';
import { HomeView } from '@/components/HomeView';

export default async function WelcomePage() {
  const session = auth0 ? await auth0.getSession() : null;
  return <HomeView
    signedIn={Boolean(session)}
    canList={Boolean(session && backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
    syntheticDemo={syntheticDemoAvailable(process.env)}
  />;
}
