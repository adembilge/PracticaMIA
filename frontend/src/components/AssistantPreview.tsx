'use client';

import Link from 'next/link';
import { useState, type FormEvent } from 'react';
import { useDemo } from '@/components/DemoProvider';

type EvidenceSource = {
  citation_id: string;
  title: string;
  official_url: string;
  section_path: string;
  excerpt: string;
};

type Answer = {
  status: 'insufficient_evidence' | 'model_not_configured'
    | 'answer_generated' | 'unverified_answer' | 'generation_unavailable';
  answer: string | null;
  sources: EvidenceSource[];
  is_demo: boolean;
};

type Props = { caseId: string; configured: boolean; signedIn: boolean };

const copy = {
  en: {
    title: 'Evidence assistant preview',
    warning: 'This feature is experimental. Use fictional questions only: no real names, addresses, identification numbers or documents. It cannot determine eligibility or prepare a government submission.',
    label: 'Your question about the demonstration',
    placeholder: 'What does the official source say about residence changes?',
    send: 'Ask',
    sending: 'Checking reviewed evidence...',
    back: 'Back to your demo case',
    login: 'Sign in to access the saved-case preview.',
    offline: 'Authentication or the backend is not configured for this preview.',
    error: 'The assistant is unavailable. No answer was generated.',
    insufficient_evidence: 'No reviewed official passages matched your question. The assistant cannot answer safely yet.',
    model_not_configured: 'Reviewed evidence was found, but an AI model has not been configured in this preview.',
    unverified_answer: 'The AI response could not be validated against the supplied citation IDs and was withheld.',
    generation_unavailable: 'The AI model could not generate an answer. Please try again later.',
    answer_generated: 'Exact quoted evidence — verify that each excerpt applies to your situation.',
    sources: 'Reviewed evidence references',
    open: 'Open official source',
    synthetic: 'Synthetic case only · This is not an official application.',
  },
  it: {
    title: 'Anteprima assistente con fonti',
    warning: 'Questa funzione è sperimentale. Usa solo domande fittizie: non inserire nomi, indirizzi, codici identificativi o documenti reali. Non valuta i requisiti né presenta domande ufficiali.',
    label: 'La tua domanda sulla dimostrazione',
    placeholder: 'Cosa dice la fonte ufficiale sul cambio di residenza?',
    send: 'Invia',
    sending: 'Verifica delle fonti approvate...',
    back: 'Torna alla pratica demo',
    login: 'Accedi per usare l’anteprima collegata alla pratica.',
    offline: 'Autenticazione o backend non configurati per questa anteprima.',
    error: 'Assistente non disponibile. Nessuna risposta generata.',
    insufficient_evidence: 'Non sono stati trovati passaggi ufficiali approvati. Non è possibile rispondere in modo affidabile.',
    model_not_configured: 'Sono disponibili fonti approvate, ma per questa anteprima non è stato configurato un modello AI.',
    unverified_answer: 'La risposta AI non ha superato il controllo degli identificativi delle citazioni e non viene mostrata.',
    generation_unavailable: 'Il modello AI non è disponibile in questo momento.',
    answer_generated: 'Citazioni testuali delle fonti: verifica che ogni estratto sia applicabile al tuo caso.',
    sources: 'Riferimenti alle fonti approvate',
    open: 'Apri la fonte ufficiale',
    synthetic: 'Pratica sintetica · Non è una domanda ufficiale.',
  },
} as const;

export function AssistantPreview({ caseId, configured, signedIn }: Props) {
  const { locale } = useDemo();
  const t = copy[locale];
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<Answer | null>(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending || question.trim().length < 2 || question.length > 180) return;
    setError('');
    setResult(null);
    setPending(true);
    try {
      const response = await fetch('/api/cases/' + encodeURIComponent(caseId) + '/assistant/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        cache: 'no-store',
        body: JSON.stringify({ question, language: locale }),
      });
      if (!response.ok) throw new Error('Assistant HTTP ' + response.status);
      const answer = (await response.json()) as Answer;
      if (!answer.is_demo || !Array.isArray(answer.sources)) throw new Error('Unexpected response');
      setResult(answer);
    } catch {
      setError(t.error);
    } finally {
      setPending(false);
    }
  }

  return <main id="main-content" tabIndex={-1} className="subpage-background">
    <div className="container account-shell">
      <span className="tiny-eyebrow">EXPERIMENTAL · PREVIEW ONLY</span>
      <h1 className="subpage-title">{t.title}</h1>
      <p className="message-box warning" role="note">{t.warning}</p>

      {!configured ? <p className="message-box notice" role="status">{t.offline}</p>
        : !signedIn ? <section className="account-panel">
          <p>{t.login}</p>
          <a className="button button-primary" href="/auth/login">Sign in / Accedi</a>
        </section>
        : <section className="account-panel">
          <form onSubmit={(event) => void submit(event)}>
            <label className="field-label" htmlFor="assistant-question">{t.label}</label>
            <textarea id="assistant-question" className="input input-textarea" rows={4}
              maxLength={180} required value={question} placeholder={t.placeholder}
              onChange={(event) => setQuestion(event.target.value)} disabled={pending} />
            <div className="form-meta"><span>{question.length}/180</span></div>
            <button type="submit" className="button button-primary"
              disabled={pending || question.trim().length < 2}>
              {pending ? t.sending : t.send}
            </button>
          </form>
          {error && <p role="alert" className="error-text">{error}</p>}
          {result && <section className="assistant-result" aria-live="polite">
            <h2>{t[result.status]}</h2>
            {result.status === 'answer_generated' && result.answer &&
              <p className="assistant-answer">{result.answer}</p>}
            {result.sources.length > 0 && <>
              <h3>{t.sources}</h3>
              <ul className="assistant-source-list">
                {result.sources.map((source) => <li key={source.citation_id}>
                  <strong>{source.title}</strong>
                  <span>{source.section_path}</span>
                  <p>{source.excerpt}</p>
                  <code>{source.citation_id}</code>
                  <a href={source.official_url} target="_blank" rel="noopener noreferrer">
                    {t.open}
                  </a>
                </li>)}
              </ul>
            </>}
          </section>}
        </section>}
      <p className="account-footnote">{t.synthetic}</p>
      <Link href={'/cases/' + encodeURIComponent(caseId)} className="back-link">{t.back}</Link>
    </div>
  </main>;
}
