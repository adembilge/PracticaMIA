import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { chatTransportAvailable } from '@/lib/chat-transport-guard.js';
import { SingleChatWorkspace } from '@/components/SingleChatWorkspace';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const session = auth0 ? await auth0.getSession() : null;
  const configured = Boolean(
    auth0 &&
    backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV) &&
    chatTransportAvailable(process.env),
  );

  return <SingleChatWorkspace
    signedIn={Boolean(session)}
    configured={configured}
    displayName={String(session?.user?.name || session?.user?.nickname || '')}
  />;
}
