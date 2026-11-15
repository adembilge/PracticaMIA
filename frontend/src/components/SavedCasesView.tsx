'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { useDemo } from '@/components/DemoProvider';
import { Icon } from '@/components/Icon';
import { LiveExampleAIGuide } from '@/components/LiveExampleAIGuide';

type SavedCase = { id: string; status: string; created_at: string };

type Props = {
  configured: boolean;
  signedIn: boolean;
  backendConfigured: boolean;
  liveAIEnabled: boolean;
};

export function SavedCasesView({ configured, signedIn, backendConfigured, liveAIEnabled }: Props) {
  const { t, locale } = useDemo();
  const router = useRouter();
  const [cases, setCases] = useState<SavedCase[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [failure, setFailure] = useState<'list' | 'create' | 'expired' | null>(null);

  const canUseApi = configured && signedIn && backendConfigured;
  const refresh = useCallback(async () => {
    if (!canUseApi) return;
    setLoading(true);
    setFailure(null);
    try {
      const response = await fetch('/api/cases', { cache: 'no-store' });
      if (response.status === 401) { setFailure('expired');return; }
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const rows: SavedCase[] = await response.json();
      setCases(rows);
    } catch {
      setFailure('list');
    } finally {
      setLoading(false);
    }
  }, [canUseApi]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function createSyntheticCase() {
    if (!canUseApi || creating) return;
    setCreating(true);
    setFailure(null);
    try {
      const response = await fetch('/api/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
        credentials: 'same-origin',
      });
      if (response.status === 401) { setFailure('expired');return; }
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const created = (await response.json()) as SavedCase;
      await refresh();
      router.push('/cases/' + encodeURIComponent(created.id));
    } catch {
      setFailure('create');
    } finally {
      setCreating(false);
    }
  }

  const isItalian = locale === 'it';
  const retry = isItalian ? 'Riprova' : 'Try again';
  const displayStatus: Record<string,string> = {
    incomplete: isItalian ? 'Da completare' : 'In progress',
    needs_information: isItalian ? 'Servono informazioni' : 'More information needed',
    unsupported: isItalian ? 'Fuori ambito' : 'Outside supported scope',
    provisionally_in_scope: isItalian ? 'Ambito confermato' : 'Scope questions complete',
  };
  return (
    <main id="main-content" tabIndex={-1} className="case-page saved-cases-page">
      <div className="container account-shell">
        <header className="case-header"><div><p className="editorial-label">{isItalian ? 'Milano · Cambio di residenza' : 'Milano · Change of residence'}</p><h1>{t.savedTitle}</h1></div></header>
        {!configured ? (
          <p role="status" className="message-box notice">{t.accountUnavailable}</p>
        ) : !signedIn ? (
          <section className="account-panel">
            <p>{t.savedSignIn}</p>
            <a href="/auth/login?returnTo=%2Fcases%2Fsaved" className="button button-primary">{t.accountLogin}</a>
          </section>
        ) : !backendConfigured ? (
          <p role="status" className="message-box notice">{t.savedBackendUnavailable}</p>
        ) : (
          <section className="account-panel saved-index">
            <div className="saved-index-header">
              <p>{isItalian ? 'Crea o riprendi un caso usando dati fittizi.' : 'Start or resume a case using fictional information.'}</p>
              <button type="button" className="button button-primary" onClick={createSyntheticCase} disabled={creating || loading || failure === 'expired'}>
                {creating ? t.savedCreating : t.savedCreate}
                <Icon name="arrowRight" size={16}/>
              </button>
            </div>
            {loading ? <p role="status" className="editorial-pending">{t.savedLoading}</p> : cases.length > 0 && (
              <ul className="saved-case-list">
                {cases.map((item) => (
                  <li key={item.id}>
                    <Link href={'/cases/' + encodeURIComponent(item.id)} className="saved-case-row">
                      <span className="saved-case-symbol"><Icon name="file" size={19}/></span>
                      <span className="saved-case-label"><strong>{displayStatus[item.status] ?? t.savedDraft}</strong>
                        <code>{item.id.slice(0, 8)}</code>
                      </span>
                      <span className="saved-case-resume">{t.savedResume} <Icon name="arrowRight" size={16}/></span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {!loading && cases.length === 0 && !failure && <div className="case-state"><Icon name="file"/><p>{t.savedEmpty}</p></div>}
            {failure && <div className="message-box warning" role="alert"><div>
              <p>{failure === 'expired' ? (isItalian ? 'La sessione è scaduta.' : 'Your session has expired.') :
                failure === 'list' ? t.savedError : t.savedCreateError}</p>
              {failure === 'expired' ?
                <a className="inline-link" href="/auth/login?returnTo=%2Fcases%2Fsaved">{t.accountLogin}</a> :
                <button className="inline-link" type="button" onClick={() => void (failure === 'list' ? refresh() : createSyntheticCase())}>{retry}</button>}
            </div></div>}
          </section>
        )}
        <Link href="/demo/synthetic" className="editorial-text-link saved-demo-link">
          {isItalian ? 'Esplora un caso fittizio' : 'Explore a fictional case'} <Icon name="arrowRight" size={16}/>
        </Link>
        {signedIn && liveAIEnabled && <LiveExampleAIGuide />}
        <p className="account-footnote">{t.accountDemoPrivacy}</p>
        <Link href="/account" className="back-link">{t.accountBack}</Link>
      </div>
    </main>
  );
}
