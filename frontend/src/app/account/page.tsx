import { auth0 } from '@/lib/auth0';
import { backendOrigin } from '@/lib/auth-configuration.js';
import { AccountView } from '@/components/AccountView';

export const dynamic = 'force-dynamic';

export default async function AccountPage() {
  const session = auth0 ? await auth0.getSession() : null;
  return (
    <AccountView
      configured={Boolean(auth0)}
      signedIn={Boolean(session)}
      name={session?.user?.name || session?.user?.nickname || ''}
      backendConfigured={Boolean(backendOrigin(process.env.BACKEND_API_URL, process.env.NODE_ENV))}
    />
  );
}
