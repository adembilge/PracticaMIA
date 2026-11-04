'use client';

import Link from 'next/link';
import { useDemo } from '@/components/DemoProvider';

type Props = {
  configured: boolean;
  signedIn: boolean;
  name: string;
  backendConfigured: boolean;
};

export function AccountView({ configured, signedIn, name, backendConfigured }: Props) {
  const { t } = useDemo();
  return (
    <main id="main-content" tabIndex={-1} className="subpage-background">
      <div className="container account-shell">
        <h1 className="subpage-title">{t.accountTitle}</h1>
        {!configured ? (
          <p role="status" className="message-box notice">{t.accountUnavailable}</p>
        ) : signedIn ? (
          <section className="account-panel">
            <p>{t.accountWelcome}{name ? ', ' + name : ''}.</p>
            <p>{backendConfigured ? t.accountConnectedBackend : t.accountBackendUnavailable}</p>
            <div className="account-actions">
              <Link href="/cases/saved" className="button button-primary">{t.accountSaved}</Link>
              <a href="/auth/logout" className="button button-outline">{t.accountLogout}</a>
            </div>
          </section>
        ) : (
          <section className="account-panel">
            <p>{t.accountSignInIntro}</p>
            <a href="/auth/login" className="button button-primary">{t.accountLogin}</a>
          </section>
        )}
        <p className="account-footnote">{t.accountDemoPrivacy}</p>
        <Link href="/cases/new" className="back-link">{t.accountDemoLink}</Link>
      </div>
    </main>
  );
}
