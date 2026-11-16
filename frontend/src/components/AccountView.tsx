'use client';

import Link from 'next/link';
import { useDemo } from '@/components/DemoProvider';
import { Icon } from '@/components/Icon';
import styles from './AccountView.module.css';

type Props = {
  configured: boolean;
  signedIn: boolean;
  name: string;
  backendConfigured: boolean;
};

export function AccountView({ configured, signedIn, name, backendConfigured }: Props) {
  const { locale, t } = useDemo();

  if (!signedIn) {
    const language = new URLSearchParams({ ui_locales: locale });
    const signIn = '/auth/login?' + language.toString();
    language.set('screen_hint', 'signup');
    const register = '/auth/login?' + language.toString();

    return (
      <main id="main-content" tabIndex={-1} className="subpage-background">
        <div className={`container ${styles.shell}`}>
          <div className={styles.card}>
            <div className={styles.intro}>
              <Icon name="file" size={28} className={styles.emblem} />
              <h1>{t.accountSignInTitle}</h1>
              <p>{t.accountSignInIntro}</p>
            </div>
            <section className={styles.access} aria-label={t.navSignIn}>
              {configured ? (
                <div className={styles.actions}>
                  <a href={signIn} className="button button-primary">
                    {t.accountLogin}<Icon name="arrowRight" size={19} />
                  </a>
                  <a href={register} className="button button-outline">
                    {t.accountRegister}
                  </a>
                </div>
              ) : <p role="status" className="message-box notice">{t.accountUnavailable}</p>}
              <Link href="/cases/new" className={styles.demoLink}>
                {t.accountDemoLink}<Icon name="arrowRight" size={16} />
              </Link>
            </section>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main id="main-content" tabIndex={-1} className="subpage-background">
      <div className="container account-shell">
        <h1 className="subpage-title">{t.accountTitle}</h1>
        <section className="account-panel">
          <p>{t.accountWelcome}{name ? ', ' + name : ''}.</p>
          <p>{backendConfigured ? t.accountConnectedBackend : t.accountBackendUnavailable}</p>
          <div className="account-actions">
            <Link href="/cases/saved" className="button button-primary">{t.accountSaved}</Link>
            <a href="/auth/logout" className="button button-outline">{t.accountLogout}</a>
          </div>
        </section>
        <Link href="/cases/new" className="back-link">{t.accountDemoLink}</Link>
      </div>
    </main>
  );
}
