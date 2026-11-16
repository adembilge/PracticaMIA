'use client';

import Link from 'next/link';
import { useRef, useState } from 'react';
import { Icon } from '@/components/Icon';
import { useDemo } from '@/components/DemoProvider';
import {
  SYNTHETIC_FACT_OPTIONS, SYNTHETIC_SCENARIOS,
  createSyntheticCase, updateSyntheticFacts, confirmSyntheticFacts,
  loadSyntheticDocument, confirmSyntheticDocumentField, reviewSyntheticDocument,
  evaluateSyntheticCase, buildSyntheticPackage, approveSyntheticPackage,
} from '@/lib/synthetic-demo.js';
import styles from './SyntheticDemoWorkspace.module.css';

const fields = [
  { key: 'previous_registration_context', values: ['in_milan_example', 'arriving_abroad_example', 'unknown'] },
  { key: 'household_context', values: ['joining_household_example', 'alone_example', 'unknown'] },
  { key: 'housing_arrangement', values: ['fictional_rental', 'other_housing_example', 'unknown'] },
] as const;

const copy = {
  en: {
    title: 'Explore a fictional case', back: 'Back', change: 'Choose another scenario',
    note: 'Use the supplied example details. This walkthrough does not file anything with ANPR.',
    steps: ['Scenario', 'Questions', 'Checklist', 'Document', 'Review', 'Summary'],
    choose: 'Choose a scenario',
    scenarios: {
      standard: ['Standard move', 'Work through each step before reviewing the draft.'],
      missing: ['Missing information', 'See what happens when an answer is unknown.'],
      unsupported: ['Different circumstances', 'See where the process stops and how to change an answer.'],
      conflict: ['Document mismatch', 'Review and correct an address that differs from the case.'],
    },
    questions: ['Were you already registered in Italy?', 'Are you joining an existing household?', 'Are you renting your new home?'],
    factLabels: ['Previous registration', 'Household arrangement', 'Housing arrangement'],
    answers: ['Yes', 'No', 'Not sure'],
    continue: 'Continue', checklist: 'Your checklist', ready: 'Review a housing document',
    readyLead: 'Check the address on the document against the address in the case.',
    outside: 'This situation needs a different route',
    outsideLead: 'The preparation steps here cover a registered resident moving alone to a rented home. Review your answers or choose another scenario.',
    missing: 'More information needed', missingLead: 'Review the unanswered items to continue.',
    edit: 'Review answers', openDocument: 'Review document', document: 'Check the document',
    load: 'Open sample document', page: 'Page 1', sample: 'Housing document',
    property: 'Property address', caseAddress: 'Address in the case', documentAddress: 'Address on the document',
    confirmed: 'Address to use', confirmAddress: 'Confirm address', review: 'Mark as reviewed',
    showReview: 'Review draft', reviewed: 'Document reviewed',
    mismatch: 'The addresses differ. Compare both values and confirm the address for this case.',
    draft: 'Review your draft', acknowledgement: 'I have checked the information above.',
    finish: 'Finish review', viewSummary: 'View summary', finished: 'Review complete',
    handoff: 'Official submission', notSubmitted: 'Not submitted', download: 'Download summary (JSON)',
    moveDate: 'Move-in date', previous: 'Previous address', start: 'Start a case',
  },
  it: {
    title: 'Esplora un caso fittizio', back: 'Indietro', change: 'Scegli un altro scenario',
    note: 'Usa i dati di esempio forniti. Questo percorso non invia alcuna domanda all’ANPR.',
    steps: ['Scenario', 'Domande', 'Lista', 'Documento', 'Verifica', 'Riepilogo'],
    choose: 'Scegli uno scenario',
    scenarios: {
      standard: ['Trasferimento standard', 'Segui i passaggi e controlla la bozza.'],
      missing: ['Informazioni mancanti', 'Scopri cosa succede quando una risposta è incerta.'],
      unsupported: ['Situazione diversa', 'Scopri dove si ferma il percorso e come modificare una risposta.'],
      conflict: ['Indirizzi discordanti', 'Controlla e correggi un indirizzo diverso da quello della pratica.'],
    },
    questions: ['Eri già iscritto all’anagrafe in Italia?', 'Entri in una famiglia anagrafica già esistente?', 'La nuova abitazione è in affitto?'],
    factLabels: ['Iscrizione anagrafica precedente', 'Composizione del nucleo', 'Situazione abitativa'],
    answers: ['Sì', 'No', 'Non so'],
    continue: 'Continua', checklist: 'La tua lista', ready: 'Controlla un documento sull’alloggio',
    readyLead: 'Confronta l’indirizzo del documento con quello della pratica.',
    outside: 'Questa situazione richiede un altro percorso',
    outsideLead: 'Questo percorso riguarda una persona già iscritta all’anagrafe che si trasferisce da sola in affitto. Verifica le risposte o scegli un altro scenario.',
    missing: 'Servono altre informazioni', missingLead: 'Controlla le risposte mancanti per continuare.',
    edit: 'Controlla le risposte', openDocument: 'Controlla il documento', document: 'Verifica il documento',
    load: 'Apri il documento di esempio', page: 'Pagina 1', sample: 'Documento sull’alloggio',
    property: 'Indirizzo dell’immobile', caseAddress: 'Indirizzo della pratica', documentAddress: 'Indirizzo nel documento',
    confirmed: 'Indirizzo da usare', confirmAddress: 'Conferma l’indirizzo', review: 'Segna come verificato',
    showReview: 'Verifica la bozza', reviewed: 'Documento verificato',
    mismatch: 'Gli indirizzi sono diversi. Confrontali e conferma quello della pratica.',
    draft: 'Verifica la bozza', acknowledgement: 'Ho controllato le informazioni qui sopra.',
    finish: 'Completa la verifica', viewSummary: 'Vedi il riepilogo', finished: 'Verifica completata',
    handoff: 'Invio ufficiale', notSubmitted: 'Non inviato', download: 'Scarica il riepilogo (JSON)',
    moveDate: 'Data del trasferimento', previous: 'Indirizzo precedente', start: 'Inizia una pratica',
  },
} as const;

type ScenarioId = keyof typeof copy.en.scenarios;

function displayAddress(value: string) {
  return value.replace(/ \(SIMULATED\)$/, '');
}

function saveSummary(value: unknown) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'practicamia-sample-not-submitted.json';
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1500);
}

export function SyntheticDemoWorkspace({ startAtDocument = false }: { startAtDocument?: boolean }) {
  const { locale } = useDemo();
  const t = copy[locale];
  const [state, setState] = useState(() => {
    const sample = createSyntheticCase('standard');
    return startAtDocument ? confirmSyntheticFacts(sample) : sample;
  });
  const [step, setStep] = useState(startAtDocument ? 3 : 0);
  const [direction, setDirection] = useState('forward');
  const [fieldChoice, setFieldChoice] = useState('');
  const [packageAccepted, setPackageAccepted] = useState(false);
  const stage = useRef<HTMLElement>(null);
  const assessment = evaluateSyntheticCase(state);
  const summary = buildSyntheticPackage(state);
  const outside = assessment.decision === 'unsupported';
  const supported = assessment.decision === 'supported';
  const complete = assessment.status === 'simulated_handoff';
  const pendingAddress = Boolean(fieldChoice && fieldChoice !== state.confirmed_document_value);
  const selectedScenario = state.scenario_id as ScenarioId;
  const maxStep = !state.facts_confirmed ? 1 : !supported ? 2
    : pendingAddress ? 3 : complete ? 5 : summary ? 4 : 3;

  function goTo(next: number) {
    if (next === step) return;
    setDirection(next < step ? 'back' : 'forward');
    setStep(next);
    requestAnimationFrame(() => stage.current?.querySelector('h2')?.focus());
  }

  function chooseScenario(id: ScenarioId) {
    setState(createSyntheticCase(id));
    setFieldChoice('');
    setPackageAccepted(false);
    goTo(1);
  }

  function reset() {
    setState(createSyntheticCase('standard'));
    setFieldChoice('');
    setPackageAccepted(false);
    goTo(0);
  }

  return <main id="main-content" className={styles.page} tabIndex={-1}>
    <div className={styles.shell}>
      <header className={styles.hero}>
        <div><h1>{t.title}</h1><p>{t.note}</p></div>
        <Link href="/cases/new" className={styles.homeLink}>{t.start}</Link>
      </header>

      <div className={styles.columns}>
        <nav className={styles.steps} aria-label={locale === 'it' ? 'Passaggi della pratica' : 'Case progress'}>
          {t.steps.map((name, i) => <button key={name} type="button"
            className={[styles.step, step === i ? styles.stepActive : '', step > i ? styles.stepDone : ''].join(' ')}
            aria-current={step === i ? 'step' : undefined}
            disabled={i > maxStep || (i === 1 && step === 0)} onClick={() => i === 0 ? reset() : goTo(i)}>
            <span>{i + 1}</span>{name}
          </button>)}
        </nav>

        <section className={styles.primary} key={step} data-direction={direction} ref={stage}>
          {step === 0 && <div className={styles.panel}>
            <h2 tabIndex={-1}>{t.choose}</h2>
            <div className={styles.scenarios}>
              {SYNTHETIC_SCENARIOS.map(({id}: {id: string}) => {
                const [title, description] = t.scenarios[id as ScenarioId];
                return <button key={id} className={styles.scenario} type="button" onClick={() => chooseScenario(id as ScenarioId)}>
                  <strong>{title}</strong><span>{description}</span><Icon name="arrowRight" size={17}/>
                </button>;
              })}
            </div>
          </div>}

          {step === 1 && <div className={styles.panel}>
            <h2 tabIndex={-1}>{t.steps[1]}</h2>
            {fields.map(({key, values}, index) => <fieldset className={styles.question} key={key}>
              <legend>{t.questions[index]}</legend>
              <div className="answer-grid">
                {values.map((value, choice) => <button key={value} type="button"
                  className={'answer-option' + (state.facts[key] === value ? ' selected' : '')}
                  aria-pressed={state.facts[key] === value} onClick={() => {
                    if (state.facts[key] === value) return;
                    setState(current => updateSyntheticFacts(current, { [key]: value }));
                    setFieldChoice('');
                    setPackageAccepted(false);
                  }}>
                  <span className="answer-radio"/>{t.answers[choice]}
                </button>)}
              </div>
            </fieldset>)}
            <div className={styles.actions}>
              <button type="button" className="button button-outline" onClick={reset}>{t.change}</button>
              <button type="button" className="button button-primary" onClick={() => {
                if (!state.facts_confirmed) setState(confirmSyntheticFacts);
                goTo(2);
              }}>{t.continue}<Icon name="arrowRight" size={17}/></button>
            </div>
          </div>}

          {step === 2 && <div className={styles.panel}>
            <h2 tabIndex={-1}>{t.checklist}</h2>
            <div className={supported ? styles.status : styles.issue} role="status">
              <strong>{supported ? t.ready : outside ? t.outside : t.missing}</strong>
              <p>{supported ? t.readyLead : outside ? t.outsideLead : t.missingLead}</p>
              {assessment.missing_fields.length > 0 && <ul>{fields.map(({key}, index) =>
                assessment.missing_fields.includes(key) && <li key={key}>{t.factLabels[index]}</li>)}</ul>}
            </div>
            <div className={styles.actions}>
              <button className={'button ' + (supported ? 'button-outline' : 'button-primary')}
                type="button" onClick={() => goTo(1)}>{t.edit}</button>
              {supported
                ? <button type="button" className="button button-primary" onClick={() => goTo(3)}>{t.openDocument}</button>
                : <button type="button" className="button button-outline" onClick={reset}>{t.change}</button>}
            </div>
          </div>}

          {step === 3 && <div className={styles.panel}>
            <h2 tabIndex={-1}>{t.document}</h2>
            <p className={styles.muted}>{t.readyLead}</p>
            {!state.sample_loaded ? <button type="button" className="button button-primary" onClick={() => {
              const loaded = loadSyntheticDocument(state);
              setState(loaded);
              setFieldChoice(loaded.extraction_value ?? '');
            }}>{t.load}<Icon name="file" size={16}/></button> : <>
              <div className={styles.documentSplit}>
                <div className={styles.mockDocument}>
                  <div className={styles.mockDocumentHeader}><strong>{t.sample}</strong><small>{t.page}</small></div>
                  <dl className={styles.summaryRows}>
                    <div><dt>{t.documentAddress}</dt><dd>{displayAddress(state.extraction_value ?? '')}</dd></div>
                    <div><dt>{t.caseAddress}</dt><dd>{displayAddress(state.facts.property_address)}</dd></div>
                  </dl>
                </div>
                <div className={styles.documentFields}>
                  <div className={styles.field}>
                    <label htmlFor="case-checked-address">{t.confirmed}</label>
                    <select id="case-checked-address"
                      value={fieldChoice || state.confirmed_document_value || state.extraction_value || ''}
                      onChange={event => { setFieldChoice(event.target.value); setPackageAccepted(false); }}>
                      {SYNTHETIC_FACT_OPTIONS.addresses.map((address: string) =>
                        <option key={address} value={address}>{displayAddress(address)}</option>)}
                    </select>
                  </div>
                  <div className={styles.actions}>
                    <button className="button button-outline" type="button" disabled={!pendingAddress && !!state.confirmed_document_value}
                      onClick={() => setState(current => confirmSyntheticDocumentField(
                        current, fieldChoice || current.extraction_value,
                      ))}>{t.confirmAddress}</button>
                    <button className="button button-primary" type="button"
                      disabled={pendingAddress || assessment.status !== 'needs_document_review'}
                      onClick={() => setState(reviewSyntheticDocument)}>{t.review}</button>
                  </div>
                </div>
              </div>
              {assessment.status === 'needs_review' && <p className={styles.issue} role="status">{t.mismatch}</p>}
              {state.document_reviewed && !pendingAddress && <p className={styles.status} role="status">{t.reviewed}</p>}
            </>}
            <div className={styles.actions}>
              <button className="button button-outline" type="button" onClick={() => goTo(2)}>{t.back}</button>
              <button className="button button-primary" type="button" disabled={!summary || pendingAddress}
                onClick={() => goTo(4)}>{t.showReview}</button>
            </div>
          </div>}

          {step === 4 && summary && !pendingAddress && <div className={styles.panel}>
            <h2 tabIndex={-1}>{t.draft}</h2>
            <dl className={styles.summaryRows}>
              <div><dt>{t.previous}</dt><dd>{displayAddress(summary.facts.previous_address)}</dd></div>
              <div><dt>{t.caseAddress}</dt><dd>{displayAddress(summary.facts.property_address)}</dd></div>
              <div><dt>{t.moveDate}</dt><dd>{summary.facts.moved_on}</dd></div>
            </dl>
            {!complete && <label className={styles.check}>
              <input type="checkbox" checked={packageAccepted} onChange={event => setPackageAccepted(event.target.checked)}/>
              <span>{t.acknowledgement}</span>
            </label>}
            <div className={styles.actions}>
              <button className="button button-outline" type="button" onClick={() => goTo(3)}>{t.back}</button>
              <button className="button button-primary" type="button" disabled={!complete && !packageAccepted} onClick={() => {
                if (!complete) setState(approveSyntheticPackage);
                goTo(5);
              }}>{complete ? t.viewSummary : t.finish}</button>
            </div>
          </div>}

          {step === 5 && complete && summary && <div className={styles.panel}>
            <h2 tabIndex={-1}>{t.finished}</h2>
            <div className={styles.handoffRow}><span>{t.handoff}</span><strong>{t.notSubmitted}</strong></div>
            <div className={styles.actions}>
              <button className="button button-outline" type="button" onClick={reset}>{t.change}</button>
              <button className="button button-primary" type="button" onClick={() => saveSummary(summary)}>{t.download}</button>
            </div>
          </div>}
        </section>

        {step > 0 && <aside className={styles.sidebar}>
          <div className={styles.sidePanel}>
            <h3>{t.scenarios[selectedScenario][0]}</h3>
            <p className={styles.muted}>{t.scenarios[selectedScenario][1]}</p>
            <button className={styles.restart} type="button" onClick={reset}>{t.change}</button>
          </div>
        </aside>}
      </div>
    </div>
  </main>;
}
