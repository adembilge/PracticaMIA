import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { syntheticDemoAvailable } from '@/lib/synthetic-demo-guard.js';
import { HomeView } from '@/components/HomeView';
import { SingleChatWorkspace } from '@/components/SingleChatWorkspace';
import { singleChatPreviewEnabled } from '@/lib/single-chat-preview.js';

export default async function WelcomePage() {
  const session = auth0 ? await auth0.getSession() : null;
  if (singleChatPreviewEnabled(process.env)) {
    return <SingleChatWorkspace
      signedIn={Boolean(session)}
      configured={Boolean(auth0 && backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
      displayName={String(session?.user?.name || session?.user?.nickname || '')}
    />;
  }
  return <HomeView
    signedIn={Boolean(session)}
    canList={Boolean(session && backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
    syntheticDemo={syntheticDemoAvailable(process.env)}
  />;
}
