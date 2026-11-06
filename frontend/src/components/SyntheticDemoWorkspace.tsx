'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useDemo } from '@/components/DemoProvider';
import {
  SYNTHETIC_DOCUMENT, SYNTHETIC_EVIDENCE, SYNTHETIC_FACT_OPTIONS,
  SYNTHETIC_REQUIREMENT, SYNTHETIC_SCENARIOS, DEMO_DISCLAIMER,
  createSyntheticCase, updateSyntheticFacts, confirmSyntheticFacts,
  loadSyntheticDocument, confirmSyntheticDocumentField, reviewSyntheticDocument,
  evaluateSyntheticCase, buildSyntheticPackage, approveSyntheticPackage,
  syntheticDocumentText,
} from '@/lib/synthetic-demo.js';
import styles from './SyntheticDemoWorkspace.module.css';

const words = {
  en: {
    tagline: 'INTERACTIVE PROTOTYPE  /  SYNTHETIC ONLY',
    title: 'Walk through a prepared case. Without entering real data.',
    subtitle: 'Explore how PracticaMIA could guide a fictional residence-change case from intake to a reviewed package. Every rule, person, document and citation shown here is invented.',
    steps: ['Scenario', 'Intake', 'Checklist', 'Document', 'Review', 'Handoff'],
    guard: 'No login. No upload. No database. No official decision. This walkthrough runs entirely in your browser and resets when the page reloads.',
    choose: 'Choose a demonstration scenario',
    continue: 'Start this scenario',
    selected: 'Selected',
    fictional: 'FICTIONAL — NOT GOVERNMENT GUIDANCE',
    factsTitle: 'Confirm the invented case facts',
    factsLead: 'All values are fixed synthetic fixtures, not actual eligibility rules. Change the selections to see how unknown or excluded cases are handled.',
    name: 'Example applicant',
    registration: 'Simulated registration context',
    household: 'Simulated household arrangement',
    housing: 'Simulated housing arrangement',
    previous: 'Invented previous address',
    destination: 'Invented destination address',
    moved: 'Fictional move date',
    inMilan: 'Example: already registered in Milan',
    unknown: 'Unknown — information missing',
    abroad: 'Example: arriving from abroad',
    alone: 'Example: applying individually',
    joining: 'Example: joining a household',
    renting: 'Example: fictional rental',
    confirmFacts: 'Confirm simulated facts and evaluate',
    editFacts: 'Edit fictional facts',
    checklistTitle: 'Rule-based assessment',
    checklistLead: 'The branch below is produced by a hard-coded mock rule, not by Italian law or approved municipal evidence.',
    decision: 'Demonstration decision',
    evidence: 'Evidence reference',
    unapproved: 'SIMULATED ONLY · not an official source',
    requirement: 'Invented example requirement',
    missing: 'Missing fields',
    blockers: 'Blocking issues',
    proceedDocs: 'Continue to sample document',
    resolve: 'Return to intake',
    unsupported: 'No package can be prepared for this scenario.',
    documentTitle: 'Inspect a fictional document',
    documentLead: 'Load an embedded sample and see a simulated extraction. No actual PDF, OCR service or private upload is used.',
    load: 'Load fictional sample',
    sample: 'Sample document text',
    extracted: 'Simulated extracted field',
    raw: 'Raw sample value (never automatically trusted)',
    confirmed: 'User-confirmed example value',
    match: 'This field must match the invented intake address. If it differs, the package remains blocked until you correct it.',
    confirmField: 'Confirm or correct extracted value',
    reviewDoc: 'Approve sample document review',
    documentReviewed: 'Sample document reviewed by participant',
    nextReview: 'Review prepared package',
    reviewTitle: 'Review the simulated preparation package',
    reviewLead: 'A preparation artifact is produced only after the mock rule matches, a sample document is reviewed and all fictional values agree.',
    preview: 'Package preview',
    notReady: 'Package unavailable. Resolve the displayed blockers before continuing.',
    acknowledgement: 'I reviewed these fictional details and understand this is not a real application.',
    approve: 'Approve fictional package',
    handoffTitle: 'Simulated handoff',
    handoffLead: 'This is the endpoint of the demo—not a government portal or a real filing.',
    outcome: 'SIMULATED PREPARATION COMPLETE',
    government: 'Government submission',
    notSubmitted: 'NOT SUBMITTED',
    sourceStatus: 'Municipal source approval',
    notApproved: 'NOT APPROVED',
    nextAction: 'In a future verified version, a person would follow approved official instructions and submit independently. This demo intentionally provides no actionable filing instructions.',
    download: 'Export fictional JSON package',
    restart: 'Restart demo',
    back: 'Back',
    technical: 'How this differs from the real MVP',
    technicalBody: 'This browser-only walkthrough demonstrates states and safeguards. It does not call the protected backend, LangGraph, database, actual OCR, LLM or official websites. Those components require separate Preview acceptance and authorized source review.',
    warning: DEMO_DISCLAIMER,
  },
  it: {
    tagline: 'PROTOTIPO INTERATTIVO  /  SOLO DATI FITTIZI',
    title: 'Esplora la preparazione di una pratica. Senza dati reali.',
    subtitle: 'Scopri come PracticaMIA potrebbe accompagnare una pratica di residenza fittizia, dalla raccolta dati al riepilogo finale. Regole, persone, documenti e citazioni sono inventati.',
    steps: ['Scenario', 'Dati', 'Requisiti', 'Documento', 'Revisione', 'Passaggio'],
    guard: 'Nessun accesso, caricamento, database o decisione ufficiale. La simulazione funziona solo nel browser e si azzera ricaricando la pagina.',
    choose: 'Scegli uno scenario dimostrativo',
    continue: 'Avvia lo scenario',
    selected: 'Selezionato',
    fictional: 'FITTIZIO — NON È UNA GUIDA UFFICIALE',
    factsTitle: 'Conferma i dati inventati della pratica',
    factsLead: 'Tutti i valori sono esempi fittizi, non condizioni legali. Modifica le risposte per vedere cosa succede se mancano dati o il caso non è supportato.',
    name: 'Richiedente di esempio',
    registration: 'Contesto anagrafico simulato',
    household: 'Composizione familiare simulata',
    housing: 'Situazione abitativa simulata',
    previous: 'Indirizzo precedente inventato',
    destination: 'Indirizzo di destinazione inventato',
    moved: 'Data del trasloco fittizia',
    inMilan: 'Esempio: già residente a Milano',
    unknown: 'Non noto — informazione mancante',
    abroad: 'Esempio: arrivo dall’estero',
    alone: 'Esempio: richiesta individuale',
    joining: 'Esempio: ingresso in altro nucleo',
    renting: 'Esempio: affitto fittizio',
    confirmFacts: 'Conferma dati simulati e valuta',
    editFacts: 'Modifica i dati fittizi',
    checklistTitle: 'Valutazione basata su regole',
    checklistLead: 'Il percorso seguente usa una regola dimostrativa, non la legge italiana né fonti comunali approvate.',
    decision: 'Esito dimostrativo',
    evidence: 'Riferimento della fonte',
    unapproved: 'SOLO SIMULAZIONE · fonte non ufficiale',
    requirement: 'Requisito di esempio inventato',
    missing: 'Dati mancanti',
    blockers: 'Blocchi',
    proceedDocs: 'Continua al documento di esempio',
    resolve: 'Torna ai dati',
    unsupported: 'Non è possibile preparare alcun pacchetto per questo scenario.',
    documentTitle: 'Esamina un documento fittizio',
    documentLead: 'Carica un esempio incorporato e guarda l’estrazione simulata. Non vengono usati PDF reali, OCR o caricamenti privati.',
    load: 'Carica esempio fittizio',
    sample: 'Testo del documento di esempio',
    extracted: 'Campo estratto simulato',
    raw: 'Valore estratto (mai considerato affidabile automaticamente)',
    confirmed: 'Valore di esempio confermato dall’utente',
    match: 'Il valore deve corrispondere all’indirizzo inventato. Se diverso, il pacchetto rimane bloccato finché non viene corretto.',
    confirmField: 'Conferma o correggi il valore',
    reviewDoc: 'Conferma revisione del documento',
    documentReviewed: 'Documento fittizio revisionato',
    nextReview: 'Verifica il pacchetto',
    reviewTitle: 'Verifica il pacchetto di preparazione simulato',
    reviewLead: 'Il riepilogo è disponibile soltanto quando la regola fittizia è rispettata e il documento è stato corretto e confermato.',
    preview: 'Anteprima del pacchetto',
    notReady: 'Pacchetto non disponibile. Risolvi i blocchi prima di procedere.',
    acknowledgement: 'Ho esaminato questi dati fittizi e so che non si tratta di una domanda reale.',
    approve: 'Approva il pacchetto fittizio',
    handoffTitle: 'Passaggio simulato',
    handoffLead: 'Questo è il termine della dimostrazione, non un portale né un invio reale.',
    outcome: 'PREPARAZIONE SIMULATA COMPLETATA',
    government: 'Invio alla Pubblica Amministrazione',
    notSubmitted: 'NON INVIATO',
    sourceStatus: 'Approvazione fonti comunali',
    notApproved: 'NON APPROVATE',
    nextAction: 'In una futura versione verificata, la persona seguirà istruzioni ufficiali approvate e invierà autonomamente la domanda. Questa demo non fornisce indicazioni operative per l’invio.',
    download: 'Esporta pacchetto JSON fittizio',
    restart: 'Ricomincia la demo',
    back: 'Indietro',
    technical: 'Differenza rispetto al vero MVP',
    technicalBody: 'Questa demo eseguita nel browser illustra stati e controlli. Non chiama backend, LangGraph, database, OCR reale, LLM o siti istituzionali. Questi componenti richiedono test Preview separati e approvazione delle fonti.',
    warning: DEMO_DISCLAIMER,
  },
} as const;

const scenarioIT: Record<string, { title: string; subtitle: string }> = {
  standard: {
    title: 'Caso fittizio completo',
    subtitle: 'Percorso positivo con dati inventati e un documento di esempio.',
  },
  missing: {
    title: 'Informazioni mancanti',
    subtitle: 'La procedura fittizia non può essere scelta senza una risposta.',
  },
  unsupported: {
    title: 'Caso non supportato',
    subtitle: 'Mostra come l’app rifiuta di preparare una pratica simulata.',
  },
  conflict: {
    title: 'Dati del documento in conflitto',
    subtitle: 'Il documento fittizio contiene un altro indirizzo: serve una correzione.',
  },
};

const statusLabels: Record<string, { en: string; it: string }> = {
  needs_information: { en: 'Information needed', it: 'Informazioni mancanti' },
  unsupported: { en: 'Unsupported example', it: 'Esempio non supportato' },
  needs_confirmation: { en: 'Facts need confirmation', it: 'Dati da confermare' },
  needs_documents: { en: 'Sample document missing', it: 'Manca il documento di esempio' },
  needs_field_confirmation: { en: 'Field confirmation needed', it: 'Campo da confermare' },
  needs_document_review: { en: 'Document review needed', it: 'Documento da revisionare' },
  needs_review: { en: 'Address conflict', it: 'Indirizzi discordanti' },
  reviewable: { en: 'Ready for simulated user review', it: 'Pronto per la revisione simulata' },
  simulated_handoff: { en: 'Simulated handoff reached', it: 'Passaggio simulato raggiunto' },
};

function saveJSON(value: unknown) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'practicamia-FICTIONAL-DEMO-NOT-SUBMITTED.json';
  document.body.append(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1500);
}

export function SyntheticDemoWorkspace() {
  const { locale } = useDemo();
  const it = locale === 'it';
  const t = words[it ? 'it' : 'en'];
  const [state, setState] = useState(() => createSyntheticCase('standard'));
  const [step, setStep] = useState(0);
  const [fieldChoice, setFieldChoice] = useState('');
  const [packageAccepted, setPackageAccepted] = useState(false);
  const evaluation = evaluateSyntheticCase(state);
  const packageData = buildSyntheticPackage(state);
  const statusText = statusLabels[evaluation.status]?.[it ? 'it' : 'en'] ?? evaluation.status;
  const selectedScenario = SYNTHETIC_SCENARIOS.find(item => item.id === state.scenario_id)!;

  const setScenario = (id: string) => {
    setState(createSyntheticCase(id));
    setFieldChoice('');
    setPackageAccepted(false);
    setStep(1);
  };

  const updateFacts = (values: Record<string, string>) => {
    setState(previous => updateSyntheticFacts(previous, values));
    setPackageAccepted(false);
  };

  const reset = () => {
    setState(createSyntheticCase('standard'));
    setStep(0);
    setFieldChoice('');
    setPackageAccepted(false);
  };

  return <main id="main-content" className={styles.page} tabIndex={-1}>
    <div className={styles.shell}>
      <header className={styles.hero}>
        <div>
          <span className={styles.eyebrow}>{t.tagline}</span>
          <h1>{t.title}</h1>
          <p>{t.subtitle}</p>
        </div>
        <Link href="/" className={styles.homeLink}>{it ? 'Torna al sito' : 'Back to website'}</Link>
      </header>

      <div className={styles.safety} role="note">
        <strong>{t.fictional}</strong>
        <span>{t.guard}</span>
      </div>

      <nav className={styles.steps} aria-label={it ? 'Passaggi della dimostrazione' : 'Demo progress'}>
        {t.steps.map((name, i) => <button key={i} type="button"
          className={[styles.step, step === i ? styles.stepActive : '', step > i ? styles.stepDone : ''].join(' ')}
          aria-current={step === i ? 'step' : undefined}
          disabled={i > step} onClick={() => setStep(i)}>
          <span>{i + 1}</span>{name}
        </button>)}
      </nav>

      <div className={styles.columns}>
        <section className={styles.primary}>
          {step === 0 && <div className={styles.panel}>
            <h2>{t.choose}</h2>
            <p className={styles.muted}>{it ? 'Scegli un percorso. Non vengono richiesti dati personali.' :
              'Choose a route. No personal information is requested.'}</p>
            <div className={styles.scenarios}>
              {SYNTHETIC_SCENARIOS.map((item) => {
                const label = it ? scenarioIT[item.id] : item;
                return <button type="button" key={item.id}
                  className={styles.scenario}
                  onClick={() => setScenario(item.id)}>
                  <strong>{label.title}</strong><span>{label.subtitle}</span>
                  <small>{t.continue} →</small>
                </button>;
              })}
            </div>
          </div>}

          {step === 1 && <div className={styles.panel}>
            <span className={styles.sectionEyebrow}>{t.steps[1]}</span>
            <h2>{t.factsTitle}</h2>
            <p className={styles.muted}>{t.factsLead}</p>
            <div className={styles.form}>
              <div className={styles.field}>
                <label>{t.name}</label><div className={styles.readonly}>{state.applicant}</div>
              </div>
              <div className={styles.field}>
                <label htmlFor="synth-registration">{t.registration}</label>
                <select id="synth-registration" value={state.facts.previous_registration_context}
                  onChange={e => updateFacts({ previous_registration_context: e.target.value })}>
                  <option value="in_milan_example">{t.inMilan}</option>
                  <option value="unknown">{t.unknown}</option>
                  <option value="arriving_abroad_example">{t.abroad}</option>
                </select>
              </div>
              <div className={styles.field}>
                <label htmlFor="synth-household">{t.household}</label>
                <select id="synth-household" value={state.facts.household_context}
                  onChange={e => updateFacts({ household_context: e.target.value })}>
                  <option value="alone_example">{t.alone}</option>
                  <option value="joining_household_example">{t.joining}</option>
                </select>
              </div>
              <div className={styles.field}>
                <label htmlFor="synth-housing">{t.housing}</label>
                <select id="synth-housing" value={state.facts.housing_arrangement}
                  onChange={e => updateFacts({ housing_arrangement: e.target.value })}>
                  <option value="fictional_rental">{t.renting}</option>
                  <option value="unknown">{t.unknown}</option>
                </select>
              </div>
              <div className={styles.field}><label>{t.previous}</label>
                <div className={styles.readonly}>{state.facts.previous_address}</div></div>
              <div className={styles.field}>
                <label htmlFor="synth-address">{t.destination}</label>
                <select id="synth-address" value={state.facts.property_address}
                  onChange={e => updateFacts({ property_address: e.target.value })}>
                  {SYNTHETIC_FACT_OPTIONS.addresses.map(addr =>
                    <option key={addr} value={addr}>{addr}</option>)}
                </select>
              </div>
              <div className={styles.field}><label>{t.moved}</label>
                <div className={styles.readonly}>{state.facts.moved_on} · {t.fictional}</div>
              </div>
            </div>
            <div className={styles.actions}>
              <button className="button button-outline" type="button" onClick={() => setStep(0)}>{t.back}</button>
              <button className="button button-primary" type="button" onClick={() => {
                setState(current => confirmSyntheticFacts(current));
                setStep(2);
              }}>{t.confirmFacts}</button>
            </div>
          </div>}

          {step === 2 && <div className={styles.panel}>
            <span className={styles.sectionEyebrow}>{t.steps[2]}</span>
            <h2>{t.checklistTitle}</h2>
            <p className={styles.muted}>{t.checklistLead}</p>
            <div className={styles.status} role="status">
              <small>{t.decision}</small><strong>{statusText}</strong>
            </div>
            {evaluation.checklist.length > 0
              ? <div className={styles.rule}>
                <strong>{t.requirement}</strong>
                <p>{SYNTHETIC_REQUIREMENT.description}</p>
                <span>{SYNTHETIC_REQUIREMENT.rule_id} · {SYNTHETIC_REQUIREMENT.document_type}</span>
                <div className={styles.evidence}>
                  <b>{t.evidence}: {SYNTHETIC_EVIDENCE.id}</b>
                  <small>{SYNTHETIC_EVIDENCE.title} · {t.unapproved}</small>
                </div>
              </div>
              : <p className={styles.warningText}>{t.unsupported}</p>}
            {evaluation.missing_fields.length > 0 && <p className={styles.issue}>
              <strong>{t.missing}: </strong>{evaluation.missing_fields.join(', ')}
            </p>}
            {evaluation.blocking_issues.length > 0 && <p className={styles.issue}>
              <strong>{t.blockers}: </strong>{evaluation.blocking_issues.join('; ')}
            </p>}
            <div className={styles.actions}>
              <button type="button" className="button button-outline" onClick={() => setStep(1)}>
                {t.editFacts}
              </button>
              {evaluation.decision === 'supported' &&
                <button type="button" className="button button-primary"
                  onClick={() => setStep(3)}>{t.proceedDocs}</button>}
            </div>
          </div>}

          {step === 3 && <div className={styles.panel}>
            <span className={styles.sectionEyebrow}>{t.steps[3]}</span>
            <h2>{t.documentTitle}</h2>
            <p className={styles.muted}>{t.documentLead}</p>
            {!state.sample_loaded
              ? <button type="button" className="button button-primary" onClick={() => {
                const updated = loadSyntheticDocument(state);
                setState(updated);
                setFieldChoice(updated.extraction_value ?? '');
              }}>{t.load}</button>
              : <>
                <div className={styles.mockDocument}>
                  <div className={styles.mockDocumentHeader}>
                    <strong>{t.sample}</strong>
                    <small>SIM-DOC-001 · PAGE 1 · SYNTHETIC</small>
                  </div>
                  <pre>{syntheticDocumentText(state)}</pre>
                </div>
                <div className={styles.evidence}>
                  <strong>{t.extracted}</strong>
                  <p>{t.raw}:</p>
                  <code>{state.extraction_value}</code>
                  <small>Page 1 · SIMULATED FIELD LOCATION · NOT OCR</small>
                </div>
                <div className={styles.field} style={{ marginTop: 20 }}>
                  <label htmlFor="synth-correction">{t.confirmed}</label>
                  <select id="synth-correction"
                    value={fieldChoice || state.confirmed_document_value || state.extraction_value || ''}
                    onChange={e => setFieldChoice(e.target.value)}>
                    {SYNTHETIC_FACT_OPTIONS.addresses.map(addr =>
                      <option key={addr} value={addr}>{addr}</option>)}
                  </select>
                  <p className={styles.muted}>{t.match}</p>
                </div>
                <div className={styles.actions}>
                  <button className="button button-outline" type="button" onClick={() => {
                    setState(current => confirmSyntheticDocumentField(
                      current, fieldChoice || current.extraction_value,
                    ));
                  }}>{t.confirmField}</button>
                  <button type="button" className="button button-primary"
                    disabled={!state.confirmed_document_value || state.document_reviewed}
                    onClick={() => setState(current => reviewSyntheticDocument(current))}>
                    {t.reviewDoc}
                  </button>
                </div>
                {state.document_reviewed && <div className={styles.status}>
                  <strong>{t.documentReviewed}</strong>
                </div>}
                {evaluation.status === 'needs_review' && <p className={styles.issue} role="alert">
                  <strong>{statusText}:</strong> {evaluation.blocking_issues.join('; ')}
                </p>}
              </>}
            <div className={styles.actions}>
              <button type="button" className="button button-outline" onClick={() => setStep(2)}>{t.back}</button>
              <button type="button" className="button button-primary" disabled={evaluation.status !== 'reviewable'}
                onClick={() => setStep(4)}>{t.nextReview}</button>
            </div>
          </div>}

          {step === 4 && <div className={styles.panel}>
            <span className={styles.sectionEyebrow}>{t.steps[4]}</span>
            <h2>{t.reviewTitle}</h2>
            <p className={styles.muted}>{t.reviewLead}</p>
            {packageData
              ? <>
                <div className={styles.preview}>
                  <div><strong>{t.preview}</strong><small>SYNTHETIC JSON · NOT AN OFFICIAL FORM</small></div>
                  <pre>{JSON.stringify(packageData, null, 2)}</pre>
                </div>
                <label className={styles.check}>
                  <input type="checkbox" checked={packageAccepted}
                    onChange={e => setPackageAccepted(e.target.checked)} />
                  <span>{t.acknowledgement}</span>
                </label>
              </>
              : <p className={styles.issue}>{t.notReady} {evaluation.blocking_issues.join('; ')}</p>}
            <div className={styles.actions}>
              <button type="button" className="button button-outline" onClick={() => setStep(3)}>{t.back}</button>
              <button type="button" className="button button-primary"
                disabled={!packageData || !packageAccepted || evaluation.status !== 'reviewable'}
                onClick={() => {
                  setState(current => approveSyntheticPackage(current));
                  setStep(5);
                }}>{t.approve}</button>
            </div>
          </div>}

          {step === 5 && <div className={styles.panel}>
            <span className={styles.sectionEyebrow}>{t.steps[5]}</span>
            <h2>{t.handoffTitle}</h2>
            <p className={styles.muted}>{t.handoffLead}</p>
            {evaluation.status === 'simulated_handoff' && packageData
              ? <div className={styles.handoff}>
                <div className={styles.outcome}>{t.outcome}</div>
                <div className={styles.handoffRow}><span>{t.government}</span><strong>{t.notSubmitted}</strong></div>
                <div className={styles.handoffRow}><span>{t.sourceStatus}</span><strong>{t.notApproved}</strong></div>
                <p>{t.nextAction}</p>
                <button type="button" className="button button-primary" onClick={() => saveJSON(packageData)}>
                  {t.download}
                </button>
              </div>
              : <p className={styles.issue}>{t.notReady}</p>}
            <div className={styles.actions}>
              <button type="button" className="button button-outline" onClick={reset}>{t.restart}</button>
            </div>
          </div>}
        </section>

        <aside className={styles.sidebar}>
          <div className={styles.sidePanel}>
            <span className={styles.eyebrow}>{t.fictional}</span>
            <h3>{it ? scenarioIT[selectedScenario.id].title : selectedScenario.title}</h3>
            <dl>
              <div><dt>CASE ID</dt><dd>{state.case_id}</dd></div>
              <div><dt>{t.decision}</dt><dd>{statusText}</dd></div>
              <div><dt>{t.sourceStatus}</dt><dd>{t.notApproved}</dd></div>
              <div><dt>{t.government}</dt><dd>{t.notSubmitted}</dd></div>
            </dl>
          </div>
          <details className={styles.details}>
            <summary>{t.technical}</summary>
            <p>{t.technicalBody}</p>
          </details>
          <p className={styles.footnote}>{t.warning}</p>
          <button type="button" className={styles.restart} onClick={reset}>{t.restart}</button>
        </aside>
      </div>
    </div>
  </main>;
}
