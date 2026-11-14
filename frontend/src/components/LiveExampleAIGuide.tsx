'use client';

import {useState} from 'react';
import {useDemo} from '@/components/DemoProvider';

type Topic = 'scope' | 'documents' | 'handoff';

const labels = {
  en: {
    title: 'Try the live AI explainer',
    detail: 'This feature contacts OpenRouter using fixed fictional examples only. No case information, documents or personal details are sent to the model.',
    scope: 'Explain how intake works',
    documents: 'Explain why conflicting documents need review',
    handoff: 'Explain the official handoff boundary',
    ask: 'Generate AI explanation',
    busy: 'Generating...',
    error: 'The free model is unavailable. You can continue using the saved case without AI.',
    warning: 'Illustrative explanation, not a verified requirement or legal decision.',
  },
  it: {
    title: 'Prova la spiegazione AI dal vivo',
    detail: 'La funzione usa OpenRouter e solo esempi fittizi predefiniti. Non invia al modello dati della pratica, documenti o dati personali.',
    scope: 'Spiega come funziona la raccolta dati',
    documents: 'Spiega perché verificare i documenti discordanti',
    handoff: 'Spiega la differenza tra preparazione e invio ufficiale',
    ask: 'Genera una spiegazione AI',
    busy: 'Generazione...',
    error: 'Il modello gratuito non è disponibile. Puoi continuare la pratica senza AI.',
    warning: 'Esempio illustrativo, non un requisito verificato o una decisione legale.',
  },
} as const;

export function LiveExampleAIGuide() {
  const {locale} = useDemo();
  const t = labels[locale];
  const [topic, setTopic] = useState<Topic>('scope');
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function generate() {
    if (busy) return;
    setBusy(true);
    setAnswer('');
    setError('');
    try {
      const response = await fetch('/api/demo/ai', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({topic, language: locale}),
      });
      const result: {response?: string} = await response.json();
      if (!response.ok || !result.response) throw new Error('unavailable');
      setAnswer(result.response);
    } catch {
      setError(t.error);
    } finally {
      setBusy(false);
    }
  }

  return <section aria-label={t.title} style={{marginTop: 22, padding: 20, border: '1px solid #d6e5e8', borderRadius: 12}}>
    <h3 style={{marginTop: 0}}>{t.title}</h3>
    <p>{t.detail}</p>
    <label className="field-label" htmlFor="fictional-ai-topic">{t.title}</label>
    <select id="fictional-ai-topic" className="input" value={topic} onChange={e => {
      setTopic(e.target.value as Topic); setAnswer(''); setError('');
    }}>
      <option value="scope">{t.scope}</option>
      <option value="documents">{t.documents}</option>
      <option value="handoff">{t.handoff}</option>
    </select>
    <button type="button" className="button button-outline" style={{marginTop: 14}} disabled={busy} onClick={() => void generate()}>
      {busy ? t.busy : t.ask}
    </button>
    {error && <p role="alert" className="error-text">{error}</p>}
    {answer && <div aria-live="polite" className="message-box notice" style={{marginTop: 14}}>
      <div><p style={{whiteSpace: 'pre-wrap'}}>{answer}</p><p><strong>{t.warning}</strong></p></div>
    </div>}
  </section>;
}
