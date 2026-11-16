'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useDemo } from '@/components/DemoProvider';
import { Icon } from '@/components/Icon';
import { createSavedCase } from '@/lib/create-saved-case';
import styles from './StartCaseView.module.css';

const copy = {
  en: {
    title: 'Start a case', place: 'Milano · Change of residence',
    lead: 'Answer a few questions about your move and get a checklist for preparing your case.',
    save: 'Prepare my case', saved: 'Saved cases',
    signedOut: 'Sign in to save your progress and return to your case later.',
    signedIn: 'Your progress is saved as you go.',
    signIn: 'Sign in to start', working: 'Creating your case…',
    explore: 'Explore a fictional case',
    exploreLead: 'Walk through the questions, document review and final summary without an account.',
    steps: ['Answer a few questions', 'Review your checklist', 'Download a draft'],
    unavailable: 'Saved cases are temporarily unavailable.',
  },
  it: {
    title: 'Inizia una pratica', place: 'Milano · Cambio di residenza',
    lead: 'Rispondi a qualche domanda sul trasferimento e ottieni una lista per preparare la pratica.',
    save: 'Prepara la mia pratica', saved: 'Pratiche salvate',
    signedOut: 'Accedi per salvare i progressi e riprendere la pratica quando vuoi.',
    signedIn: 'I progressi vengono salvati durante la compilazione.',
    signIn: 'Accedi per iniziare', working: 'Creazione della pratica…',
    explore: 'Esplora un caso fittizio',
    exploreLead: 'Prova le domande, la verifica del documento e il riepilogo senza un account.',
    steps: ['Rispondi alle domande', 'Controlla la lista', 'Scarica una bozza'],
    unavailable: 'Le pratiche salvate non sono al momento disponibili.',
  },
} as const;

const login = '/auth/login?returnTo=%2Fcases%2Fnew';

export function StartCaseView({signedIn, canSave, canExplore}: {
  signedIn: boolean; canSave: boolean; canExplore: boolean;
}) {
  const router = useRouter();
  const { locale, t } = useDemo();
  const c = copy[locale];
  const [pending, setPending] = useState(false);
  const [expired, setExpired] = useState(false);
  const [error, setError] = useState(false);

  async function start() {
    if (pending) return;
    setPending(true);
    setError(false);
    try {
      const created = await createSavedCase();
      if ('expired' in created) {
        setExpired(true);
        setPending(false);
        return;
      }
      router.push('/cases/' + encodeURIComponent(created.id));
    } catch {
      setError(true);
      setPending(false);
    }
  }

  return <main id="main-content" tabIndex={-1} className={styles.page}>
    <div className={styles.shell}>
      <Link className="editorial-text-link" href="/"><Icon name="arrowLeft" size={16}/>{t.back}</Link>
      <header className={styles.intro}>
        <p className="editorial-label">{c.place}</p>
        <h1>{c.title}</h1>
        <p>{c.lead}</p>
      </header>
      <div className={styles.layout}>
        <section className={styles.primary} aria-labelledby="start-saved-title">
          <div className={styles.icon}><Icon name="home" size={24}/></div>
          <h2 id="start-saved-title">{c.save}</h2>
          <p>{!canSave ? c.unavailable : signedIn && !expired ? c.signedIn : c.signedOut}</p>
          <ol className={styles.steps}>
            {c.steps.map((step, index) => <li key={step}><span>{index + 1}</span>{step}</li>)}
          </ol>
          {canSave && <div className={styles.actions}>
            {signedIn && !expired
              ? <button type="button" className="button button-primary" aria-busy={pending}
                  disabled={pending} onClick={() => void start()}>{pending ? c.working : t.savedCreate}<Icon name="arrowRight" size={17}/></button>
              : <a className="button button-primary" href={login}>{c.signIn}<Icon name="arrowRight" size={17}/></a>}
            {signedIn && !expired && <Link href="/cases/saved" className="editorial-text-link">{c.saved}</Link>}
          </div>}
          {error && <p className="error-text" role="alert">{t.savedCreateError}</p>}
        </section>
        {canExplore && <Link href="/demo/synthetic" className={styles.example}>
          <div className={styles.icon}><Icon name="file" size={23}/></div>
          <h2>{c.explore}</h2>
          <p>{c.exploreLead}</p>
          <span className={styles.arrow}><Icon name="arrowRight" size={18}/></span>
        </Link>}
      </div>
    </div>
  </main>;
}
