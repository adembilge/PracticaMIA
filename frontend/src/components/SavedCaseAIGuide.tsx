'use client';

import {useEffect, useState} from 'react';
import {useDemo, type Answer} from '@/components/DemoProvider';
import {getCaseGuidancePlan} from '@/lib/case-guidance.js';

type Topic = 'next_step' | 'explain_status';
type Props = {
  caseId: string;
  snapshot: {status: string; scope_answers: Answer[]};
};

const translations = {
  en: {
    title:'AI guidance for this saved case',
    subtitle:'The next step below is calculated from the answers saved in your case, not a fictional example.',
    modelNotice:'OpenRouter receives only the abstract workflow status and question number. It does not receive your answers, identity, addresses, documents or case ID.',
    summary:'Case status',
    next:'Recommended product action',
    question:'Question needing attention',
    prompt:'What should I do next?',
    explain:'Explain this case status',
    loading:'Explaining…',
    offline:'The free AI model is unavailable. Your case-specific next action above still works.',
    aiLabel:'AI explanation (not legal or verified document advice)',
    warning:'The five questions do not check citizenship, registered lease details, personal eligibility or document requirements. No application has been submitted.',
    invalid:'Your saved answers are not ready for AI guidance.',
    requestError:'Case guidance could not be loaded. Check your connection and sign in again.',
  },
  it: {
    title:'Guida AI per questa pratica salvata',
    subtitle:'Il prossimo passo deriva dalle risposte salvate nella pratica, non da un esempio inventato.',
    modelNotice:'OpenRouter riceve solo lo stato astratto e il numero della domanda. Non riceve risposte, identità, indirizzi, documenti o ID della pratica.',
    summary:'Stato della pratica',
    next:'Prossima azione consigliata nel prodotto',
    question:'Domanda da chiarire',
    prompt:'Qual è il prossimo passo?',
    explain:'Spiega lo stato di questa pratica',
    loading:'Elaborazione…',
    offline:'Il modello AI gratuito non è disponibile. Il prossimo passo sopra resta utilizzabile.',
    aiLabel:'Spiegazione AI (non è una verifica legale o documentale)',
    warning:'Le cinque domande non verificano cittadinanza, registrazione del contratto, requisiti personali o documenti necessari. Non è stata inviata alcuna domanda.',
    invalid:'Le risposte salvate non sono pronte per la guida AI.',
    requestError:'Impossibile caricare la guida. Controlla la connessione e l’accesso.',
  },
} as const;

export function SavedCaseAIGuide({caseId, snapshot}: Props) {
  const {locale} = useDemo();
  const t = translations[locale];
  const plan = getCaseGuidancePlan({
    status:snapshot.status,
    answers:snapshot.scope_answers,
  },locale);
  const [busy,setBusy] = useState(false);
  const [explanation,setExplanation] = useState<string|null>(null);
  const [error,setError] = useState('');
  const [attempted,setAttempted] = useState(false);

  // Any edit invalidates earlier model output; it must never follow stale answers.
  const fingerprint = snapshot.status + ':' + snapshot.scope_answers.join(',');
  useEffect(() => {setExplanation(null);setAttempted(false);setError('');},[fingerprint]);

  async function explain(topic: Topic) {
    if (!plan || busy) return;
    setBusy(true);
    setError('');
    setExplanation(null);
    setAttempted(false);
    try {
      const res = await fetch('/api/cases/' + caseId + '/guidance', {
        method:'POST',
        credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({topic,language:locale}),
        cache:'no-store',
      });
      if (!res.ok) throw new Error('Guidance unavailable');
      const data: {
        guidance?: {status?:string;answered_count?:number;next_question_index?:number|null};
        ai_explanation?:string|null;
      } = await res.json();
      if (data.guidance?.status!==plan.status ||
          data.guidance?.answered_count!==plan.answered_count ||
          data.guidance?.next_question_index!==plan.next_question_index) {
        throw new Error('Saved case changed');
      }
      setExplanation(typeof data.ai_explanation==='string'?data.ai_explanation:null);
      setAttempted(true);
    } catch {
      setError(t.requestError);
    } finally {setBusy(false);}
  }

  return <section aria-label={t.title} style={{padding:18,marginTop:20,border:'1px solid #d6e5e8',borderRadius:12}}>
    <h3 style={{marginTop:0}}>{t.title}</h3>
    <p>{t.subtitle}</p>
    {!plan ? <p role="status">{t.invalid}</p> : <>
      <p><strong>{t.summary}:</strong> {plan.summary}</p>
      <p><strong>{t.next}:</strong> {plan.next_step}</p>
      {plan.next_question_index!==null && <p><strong>{t.question}:</strong> {plan.next_question_index+1}. {plan.answered_count>=plan.next_question_index+1
          ? plan.answers[plan.next_question_index]?.question
          : (locale==='it' ? 'Rispondi alla prossima domanda di ambito.' : 'Answer the next scope question.')}</p>}
      <p style={{fontSize:13,opacity:0.86}}>{t.modelNotice}</p>
      <div style={{display:'flex',flexWrap:'wrap',gap:8,marginTop:12}}>
        <button type="button" className="button button-outline" disabled={busy}
          onClick={()=>void explain('next_step')}>{busy?t.loading:t.prompt}</button>
        <button type="button" className="button button-outline" disabled={busy}
          onClick={()=>void explain('explain_status')}>{t.explain}</button>
      </div>
      {explanation && <div aria-live="polite" className="message-box notice" style={{marginTop:14}}>
        <div><strong>{t.aiLabel}</strong><p style={{whiteSpace:'pre-wrap'}}>{explanation}</p></div>
      </div>}
      {attempted&&!explanation&&<p role="status">{t.offline}</p>}
      {error&&<p role="alert" className="error-text">{error}</p>}
      <p style={{fontSize:12,opacity:0.82,marginTop:14}}>{t.warning}</p>
    </>}
  </section>;
}
