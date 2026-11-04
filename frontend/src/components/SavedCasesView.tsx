'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { useDemo } from '@/components/DemoProvider';

type SavedCase = { id: string; status: string; created_at: string };

type Props = {
  configured: boolean;
  signedIn: boolean;
  backendConfigured: boolean;
};

export function SavedCasesView({ configured, signedIn, backendConfigured }: Props) {
  const { t } = useDemo();
  const router = useRouter();
  const [cases, setCases] = useState<SavedCase[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const canUseApi = configured && signedIn && backendConfigured;
  const refresh = useCallback(async () => {
    if (!canUseApi) return;
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/cases', { cache: 'no-store' });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const rows: SavedCase[] = await response.json();
      setCases(rows);
    } catch {
      setError(t.savedError);
    } finally {
      setLoading(false);
    }
  }, [canUseApi, t.savedError]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function createSyntheticCase() {
    if (!canUseApi || creating) return;
    setCreating(true);
    setError('');
    try {
      const response = await fetch('/api/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const created = (await response.json()) as SavedCase;
      await refresh();
      router.push('/cases/' + encodeURIComponent(created.id));
    } catch {
      setError(t.savedCreateError);
    } finally {
      setCreating(false);
    }
  }

  return (
    <main id="main-content" tabIndex={-1} className="subpage-background">
      <div className="container account-shell">
        <h1 className="subpage-title">{t.savedTitle}</h1>
        {!configured ? (
          <p role="status" className="message-box notice">{t.accountUnavailable}</p>
        ) : !signedIn ? (
          <section className="account-panel">
            <p>{t.savedSignIn}</p>
            <a href="/auth/login" className="button button-primary">{t.accountLogin}</a>
          </section>
        ) : !backendConfigured ? (
          <p role="status" className="message-box notice">{t.savedBackendUnavailable}</p>
        ) : (
          <section className="account-panel">
            <p>{t.savedSyntheticOnly}</p>
            <button type="button" className="button button-primary" onClick={createSyntheticCase} disabled={creating || loading}>
              {creating ? t.savedCreating : t.savedCreate}
            </button>
            {loading ? <p role="status">{t.savedLoading}</p> : (
              <ul className="saved-case-list">
                {cases.map((item) => (
                  <li key={item.id}>
                    <span>{t.savedDraft}: {item.status}</span>
                    <code>{item.id.slice(0, 8)}</code>
                    <Link href={'/cases/' + encodeURIComponent(item.id)} className="inline-link">
                      {t.savedResume}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {!loading && cases.length === 0 && !error && <p>{t.savedEmpty}</p>}
            {error && <p role="alert" className="error-text">{error}</p>}
          </section>
        )}
        <p className="account-footnote">{t.accountDemoPrivacy}</p>
        <Link href="/account" className="back-link">{t.accountBack}</Link>
      </div>
    </main>
  );
}
