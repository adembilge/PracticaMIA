'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useDemo } from '@/components/DemoProvider';
import { Icon } from '@/components/Icon';
import { DocumentProgress } from '@/components/DocumentProgress';
import styles from './PreparationPreview.module.css';
import { serializeReviewedPreparationPackage, serializeSyntheticAnprDraft, serializeSyntheticAnprText } from '@/lib/preparation-preview';

type ChecklistItem = {
  rule_id: string;
  description: string;
  required_document_types: string[];
  evidence_refs: string[];
};
type PackageData = {
  data: Record<string, unknown>;
  review_digest: string;
};
type DocumentValidation = {
  status: 'no_documents' | 'needs_extraction' | 'needs_confirmation' |
    'needs_review' | 'unreadable' | 'conflict' | 'verified';
  document_count: number;
  not_legal_validation: true;
  conflicts: {
    kind: 'case_document_mismatch' | 'cross_document_mismatch';
    field: string;
    document_ids: string[];
  }[];
  needs_extraction: string[];
  needs_confirmation: string[];
  needs_review: string[];
  unreadable: string[];
};
type Assessment = {
  status: string;
  next_action: string;
  blocking_issues: string[];
  document_review: DocumentValidation;
  rules: {
    decision: string;
    missing_fields: string[];
    evidence_refs: string[];
    checklist: ChecklistItem[];
  };
  package: PackageData | null;
};
type ScopeField = 'citizenship_class' | 'registration_context' | 'destination_municipality' | 'household_scope' | 'housing_basis';
type ScopeQuestion = {
  field: ScopeField;
  label_en: string;
  label_it: string;
  options: { value: string; label_en: string; label_it: string }[];
};
type ScopeIntake = {
  status: 'needs_information' | 'invalid_input' | 'outside_first_candidate' | 'candidate_scope_complete';
  answered_count: number;
  total_questions: number;
  next_question: ScopeQuestion | null;
  excluded_by: string | null;
  is_legal_assessment: false;
};
type Snapshot = {
  is_demo: true;
  confirmed_facts: Record<string, string | boolean | number>;
  intake: ScopeIntake;
  workflow: Assessment;
  user_reviewed: boolean;
};
type Candidate = {
  field_name: string;
  raw_value: string;
  page: number;
  evidence_span: string;
  verification_state: string;
};
type DocumentSummary = {
  id: string;
  document_type: string;
  media_type: string;
  extraction_status: string;
  candidates: Candidate[];
  confirmed_fields: Record<string, string>;
  status: string;
};
type DocumentOperation = { kind: 'upload' } | { kind: 'extract'; id: string };
type GuideResult = {
  action: 'intake' | 'evidence' | 'case_status' | 'documents' | 'next_step';
  status: string;
  message: string;
  answer?: string | null;
  answer_status?: string;
  mode: 'model_selected' | 'guided_fallback';
  next_question: ScopeQuestion | null;
  references: ReferenceEvidence['references'];
  blocking_issues?: string[];
  next_action?: string;
  tool_actions?: string[];
  is_demo: true;
  is_legal_assessment: false;
  government_submission_status: 'not_submitted';
  history_saved?: boolean;
};
type ConversationTurn = {
  id: string;
  question: string;
  answer: string;
  action: string;
  status: string;
  language: string;
  next_action: string | null;
  created_at: string;
  citation_status?: 'current' | 'historical' | 'unknown' | 'unavailable';
  citations?: {
    source_id: string;
    source_version_id: string;
    passage_id: string;
    source_revision: number;
    status: 'current' | 'historical';
  }[];
};
type ConversationResponse = {
  turns: ConversationTurn[];
  is_demo: true;
  historical_only: true;
  government_submission_status: 'not_submitted';
};
type ReferenceEvidence = {
  status: 'reference_only' | 'partial_or_unavailable';
  personalized_requirements: false;
  is_demo: true;
  references: {
    citation_id: string;
    title: string;
    official_url: string;
    excerpt: string;
    reviewed_at: string;
  }[];
};
type AnprDraftField = {
  key: string; label_en: string; label_it: string; value: string;
  required_in_inspected_guide: boolean; input_kind: string; valid: boolean; guide_page: string;
};
type AnprDraft = {
  artifact_type: 'synthetic_anpr_field_transcription_draft';
  simulation_only: true; official_form: false;
  government_submission_status: 'NOT_SUBMITTED';
  source_currentness_verified: false;
  state: string; missing_fields: string[];
  sections: { id: string; title_en: string; title_it: string; fields: AnprDraftField[] }[];
  official_handoff: { title: string; url: string; user_only: true };
};
type Props = { caseId: string; signedIn: boolean; configured: boolean };

const preparationSteps = [
  { id: 'preparation-intake', en: 'Case details', it: 'Dati della pratica', icon: 'list' },
  { id: 'preparation-guide', en: 'Case guide', it: 'Assistente', icon: 'sparkle' },
  { id: 'preparation-evidence', en: 'Checklist and sources', it: 'Attività e fonti', icon: 'shield' },
  { id: 'synthetic-documents', en: 'Synthetic documents', it: 'Documenti sintetici', icon: 'file' },
  { id: 'preparation-package', en: 'Preparation summary', it: 'Riepilogo', icon: 'check' },
] as const;

type PreparationStep = typeof preparationSteps[number]['id'];

function stepFromHash(): PreparationStep {
  return preparationSteps.find(step => '#' + step.id === window.location.hash)?.id
    ?? 'preparation-intake';
}

class PreviewRequestError extends Error {
  constructor(readonly status: number) {
    super('Preview request failed');
  }
}


export function PreparationPreview({ caseId, signedIn, configured }: Props) {
  const { locale } = useDemo();
  const it = locale === 'it';
  const base = '/api/cases/' + encodeURIComponent(caseId) + '/preparation';
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [referenceEvidence, setReferenceEvidence] = useState<ReferenceEvidence | null>(null);
  const [anprDraft, setAnprDraft] = useState<AnprDraft | null>(null);
  const [guideQuestion, setGuideQuestion] = useState('');
  const [guideResult, setGuideResult] = useState<GuideResult | null>(null);
  const [guideBusy, setGuideBusy] = useState(false);
  const [guideHistory, setGuideHistory] = useState<ConversationTurn[]>([]);
  const [facts, setFacts] = useState<Record<string, string>>({
    citizenship_class: '',
    registration_context: '',
    destination_municipality: '',
    household_scope: '',
    housing_basis: '',
    synthetic_eligibility: '',
    housing_arrangement: '',
    property_address: '',
  });
  const [documentType, setDocumentType] = useState('fictional_agreement');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [syntheticAcknowledged, setSyntheticAcknowledged] = useState(false);
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [activeStep, setActiveStep] = useState<PreparationStep>('preparation-intake');
  const heading = useRef<HTMLHeadingElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [loadStatus, setLoadStatus] = useState<number | 'failed' | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [documentOperation, setDocumentOperation] = useState<DocumentOperation | null>(null);
  const [handoff, setHandoff] = useState<{ links: { title: string; official_url: string }[] } | null>(null);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const [state, docs, sources, anpr, conversation] = await Promise.all([
      fetch(base, { cache: 'no-store', signal }),
      fetch(base + '/documents', { cache: 'no-store', signal }),
      fetch(base + '/reference-evidence', { cache: 'no-store', signal })
        .catch(() => null),
      fetch(base + '/anpr-draft', { cache: 'no-store', signal })
        .catch(() => null),
      fetch(base + '/conversation', { cache: 'no-store', signal })
        .catch(() => null),
    ]);
    if (!state.ok || !docs.ok) throw new PreviewRequestError(!state.ok ? state.status : docs.status);
    const saved = await state.json() as Snapshot;
    const list = await docs.json() as DocumentSummary[];
    if (!saved.is_demo || !saved.intake || saved.intake.is_legal_assessment !== false ||
      !Array.isArray(list)) throw new Error('Invalid preview data');
    if (signal?.aborted) return;
    if (conversation?.ok) {
      const history = await conversation.json().catch(() => null) as ConversationResponse | null;
      setGuideHistory(
        history?.is_demo === true && history.historical_only === true &&
        history.government_submission_status === 'not_submitted' &&
        Array.isArray(history.turns) ? history.turns : [],
      );
    } else {
      setGuideHistory([]);
    }
    // Reference evidence is optional; retrieval failures must not break
    // the private case workspace or silently invent a citation.
    if (sources?.ok) {
      const evidence = await sources.json().catch(() => null) as ReferenceEvidence | null;
      setReferenceEvidence(
        evidence?.is_demo && evidence.personalized_requirements === false &&
        Array.isArray(evidence.references) ? evidence : null,
      );
    } else {
      setReferenceEvidence(null);
    }
    let normalizedDraft: AnprDraft | null = null;
    if (anpr?.ok) {
      const candidate = await anpr.json().catch(() => null) as AnprDraft | null;
      if (candidate?.artifact_type === 'synthetic_anpr_field_transcription_draft' &&
          candidate.simulation_only === true && candidate.official_form === false &&
          candidate.government_submission_status === 'NOT_SUBMITTED' &&
          candidate.source_currentness_verified === false &&
          Array.isArray(candidate.sections) && Array.isArray(candidate.missing_fields)) {
        normalizedDraft = candidate;
      }
    }
    setAnprDraft(normalizedDraft);
    const savedFields: Record<string, string> = {
      citizenship_class: String(saved.confirmed_facts.citizenship_class ?? ''),
      registration_context: String(saved.confirmed_facts.registration_context ?? ''),
      destination_municipality: String(saved.confirmed_facts.destination_municipality ?? ''),
      household_scope: String(saved.confirmed_facts.household_scope ?? ''),
      housing_basis: String(saved.confirmed_facts.housing_basis ?? ''),
      synthetic_eligibility: String(saved.confirmed_facts.synthetic_eligibility ?? ''),
      housing_arrangement: String(saved.confirmed_facts.housing_arrangement ?? ''),
      property_address: String(saved.confirmed_facts.property_address ?? ''),
    };
    for (const section of normalizedDraft?.sections ?? []) {
      for (const field of section.fields) {
        savedFields[field.key] = String(saved.confirmed_facts[field.key] ?? '');
      }
    }
    if (signal?.aborted) return;
    setFacts(savedFields);
    setDocuments(list);
    setSnapshot(saved);
  }, [base]);

  useEffect(() => {
    if (!configured || !signedIn) return;
    const controller = new AbortController();
    void refresh(controller.signal).catch(error => {
      if (!controller.signal.aborted) {
        setLoadStatus(error instanceof PreviewRequestError ? error.status : 'failed');
      }
    });
    return () => controller.abort();
  }, [configured, signedIn, refresh, loadAttempt]);

  useEffect(() => {
    function syncStep() {
      setActiveStep(stepFromHash());
      setError('');
      setMessage('');
    }
    syncStep();
    window.addEventListener('popstate', syncStep);
    window.addEventListener('hashchange', syncStep);
    return () => {
      window.removeEventListener('popstate', syncStep);
      window.removeEventListener('hashchange', syncStep);
    };
  }, []);

  function openStep(next: PreparationStep) {
    if (next === activeStep) return;
    window.history.pushState(null, '', '#' + next);
    setError('');
    setMessage('');
    setActiveStep(next);
    requestAnimationFrame(() => heading.current?.focus());
  }

  function feedback(error: unknown, fallback: string) {
    if (error instanceof PreviewRequestError && error.status === 401) {
      return it ? 'La sessione è scaduta. Accedi di nuovo per continuare.' :
        'Your session has expired. Sign in again to continue.';
    }
    return fallback;
  }

  async function mutate(url: string, method: string, body?: unknown): Promise<unknown> {
    const response = await fetch(url, {
      method,
      credentials: 'same-origin',
      ...(body !== undefined ? {
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      } : {}),
    });
    if (!response.ok) throw new PreviewRequestError(response.status);
    if (response.status === 204) return null;
    return response.json() as Promise<unknown>;
  }

  async function askGuide() {
    if (guideBusy || guideQuestion.trim().length < 2) return;
    setGuideBusy(true);
    setGuideResult(null);
    setError('');
    try {
      const result = await mutate(base + '/guide', 'POST', {
        question: guideQuestion.trim(),
        language: locale,
      }) as GuideResult;
      if (result.is_demo !== true || result.is_legal_assessment !== false ||
          result.government_submission_status !== 'not_submitted') {
        throw new Error('Guide returned an unexpected response');
      }
      setGuideResult(result);
      if (result.history_saved === true) {
        const saved = await fetch(base + '/conversation', { cache: 'no-store' });
        if (saved.ok) {
          const history = await saved.json() as ConversationResponse;
          if (history.is_demo && history.historical_only &&
              history.government_submission_status === 'not_submitted' &&
              Array.isArray(history.turns)) setGuideHistory(history.turns);
        }
      }
    } catch (err) {
      setError(feedback(err, it ? 'Non è stato possibile ottenere una risposta. Riprova.' : 'The guide could not respond. Try again.'));
    } finally {
      setGuideBusy(false);
    }
  }

  async function saveFacts() {
    // Preserve other user-confirmed scalar fields when the guided form saves.
    // Clearing a field explicitly removes the old answer.
    const confirmed_facts: Record<string, string | number | boolean> = {
      ...(snapshot?.confirmed_facts ?? {}),
    };
    for (const [key, value] of Object.entries(facts)) {
      if (value.trim()) confirmed_facts[key] = value;
      else delete confirmed_facts[key];
    }
    await mutate(base + '/facts', 'PUT', { confirmed_facts });
  }

  async function resetScope() {
    const confirmed_facts = { ...(snapshot?.confirmed_facts ?? {}) };
    for (const field of ['citizenship_class', 'registration_context',
      'destination_municipality', 'household_scope', 'housing_basis']) {
      delete confirmed_facts[field];
    }
    await mutate(base + '/facts', 'PUT', { confirmed_facts });
  }

  async function run(
    action: () => Promise<void>,
    success: string,
    failure?: (error: unknown) => string,
    operation?: DocumentOperation,
  ) {
    setBusy(true);
    if (operation) setDocumentOperation(operation);
    setError('');
    setMessage('');
    setHandoff(null);
    try {
      await action();
      await refresh();
      setMessage(success);
    } catch (err) {
      setError(feedback(err, failure?.(err) ?? (it ? 'Non è stato possibile completare l’operazione. Riprova.' : 'This action could not be completed. Try again.')));
    } finally {
      if (operation) setDocumentOperation(null);
      setBusy(false);
    }
  }

  async function downloadAnprWorksheet(format: 'json' | 'txt' = 'json') {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const response = await fetch(base + '/anpr-draft', { cache: 'no-store' });
      if (!response.ok) throw new PreviewRequestError(response.status);
      const latest = await response.json() as AnprDraft;
      const serialized = format === 'txt' ? serializeSyntheticAnprText(latest) :
        serializeSyntheticAnprDraft(latest);
      const blob = new Blob([serialized], { type: format === 'txt' ?
        'text/plain;charset=utf-8' : 'application/json;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'practicamia-anpr-worksheet-' + caseId + '.' + format;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(feedback(err, it ? 'Non è stato possibile scaricare la scheda. Riprova.' : 'The worksheet could not be downloaded. Try again.'));
    } finally {
      setBusy(false);
    }
  }

  async function downloadReviewedPackage() {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      // Re-check current source approvals, review digest, and package state
      // before exporting: cached UI data may have become invalid.
      const response = await fetch(base, { cache: 'no-store' });
      if (!response.ok) throw new PreviewRequestError(response.status);
      const latest = await response.json() as Snapshot;
      const prepared = latest.workflow?.package;
      if (!latest.is_demo || !latest.user_reviewed ||
          latest.workflow.status !== 'reviewable' || !prepared ||
          prepared.review_digest !== snapshot?.workflow.package?.review_digest) {
        throw new Error('This review is no longer current; reload and review again');
      }
      const serialized = serializeReviewedPreparationPackage(
        prepared.data, prepared.review_digest,
      );
      const blob = new Blob([serialized], { type: 'application/json;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'practicamia-synthetic-preparation-' + caseId + '.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      await refresh();
    } catch (err) {
      setError(feedback(err, it ? 'Il riepilogo non è disponibile. Controlla la revisione e riprova.' : 'The summary is unavailable. Check the review and try again.'));
    } finally {
      setBusy(false);
    }
  }

  const step = preparationSteps.find(item => item.id === activeStep) ?? preparationSteps[0];
  const back = '/cases/' + encodeURIComponent(caseId);
  const login = '/auth/login?returnTo=' + encodeURIComponent(back + '/preparation#' + activeStep);
  const tooLarge = Boolean(uploadFile && uploadFile.size > 2 * 1024 * 1024);

  return <main className={'case-page ' + styles.page} id="main-content" tabIndex={-1}>
    <div className="container">
      <header className={'case-header ' + styles.header}>
        <div>
          <p className="editorial-label">{it ? 'Ambiente di test' : 'Test environment'}</p>
          <h1>{it ? 'Preparazione della pratica' : 'Case preparation'}</h1>
        </div>
        <Link className="editorial-text-link" href={back}><Icon name="arrowLeft" size={16}/> {it ? 'Torna alla pratica' : 'Back to case'}</Link>
      </header>

      {(!configured || !signedIn || (!snapshot && loadStatus !== null)) ?
        <section className={styles.state} role="alert">
          <Icon name={loadStatus === 401 || !signedIn ? 'lock' : 'alert'} size={24}/>
          <div>
            <h2>{!configured ? (it ? 'Anteprima non configurata' : 'Preview is not configured') :
              !signedIn || loadStatus === 401 ? (it ? 'Accedi per continuare' : 'Sign in to continue') :
              loadStatus === 404 ? (it ? 'Pratica non disponibile' : 'Case unavailable') :
              (it ? 'Impossibile caricare l’anteprima' : 'Could not load the preview')}</h2>
            <div className={styles.actions}>
              {configured && (!signedIn || loadStatus === 401) &&
                <a href={login} className="button button-primary">{it ? 'Accedi' : 'Sign in'}</a>}
              {configured && signedIn && loadStatus !== 401 && loadStatus !== 404 &&
                <button type="button" className="button button-primary" onClick={() => {
                  setLoadStatus(null);
                  setLoadAttempt(attempt => attempt + 1);
                }}>{it ? 'Riprova' : 'Try again'}</button>}
              <Link className="button button-outline" href="/cases/saved">{it ? 'Pratiche salvate' : 'Saved cases'}</Link>
            </div>
          </div>
        </section> : !snapshot ?
        <p className="editorial-pending" role="status">{it ? 'Caricamento della pratica…' : 'Loading your case…'}</p> :
        <div className={styles.layout}>
          <nav className={styles.navigation} aria-label={it ? 'Passaggi di preparazione' : 'Preparation steps'}>
            {preparationSteps.map(item => <button type="button" key={item.id}
              aria-current={item.id === activeStep ? 'step' : undefined}
              disabled={busy || guideBusy} onClick={() => openStep(item.id)}>
              <Icon name={item.icon} size={18}/><span>{it ? item.it : item.en}</span>
            </button>)}
          </nav>
          <div className={styles.content}>
            <div className={styles.safety}>
              <Icon name="shield" size={18}/>
              <p>{it ? 'Usa solo dati e documenti inventati. L’invio ufficiale avviene su ANPR.' :
                'Use fictional details and documents only. Official submission takes place on ANPR.'}</p>
            </div>
            <section className={styles.panel} id={activeStep} aria-labelledby="preparation-step-title"
              aria-busy={(busy && !documentOperation) || guideBusy}>
              <h2 id="preparation-step-title" ref={heading} tabIndex={-1}>{it ? step.it : step.en}</h2>
              {activeStep !== 'synthetic-documents' && message && <p role="status" className={styles.success}>{message}</p>}
              {activeStep !== 'synthetic-documents' && error && <p role="alert" className={styles.error}>{error}</p>}

              <div hidden={activeStep !== 'preparation-intake'}>
              <section aria-busy={busy}>
                <h3>{it ? 'Domande guidate' : 'Guided intake'}</h3>
                <p>{it
                  ? 'Queste domande verificano soltanto se un caso fittizio corrisponde al primo scenario proposto. Non determinano diritti o requisiti legali.'
                  : 'These questions only check whether a fictional case matches the first proposed product scenario. They do not determine legal eligibility or requirements.'}</p>
                {snapshot?.intake && <p aria-live="polite">
                  {it ? 'Risposte di inquadramento' : 'Scope answers'}: {snapshot.intake.answered_count} / {snapshot.intake.total_questions}
                </p>}
                {snapshot?.intake?.next_question ? <div className={styles.fields}>
                  <label>
                    {it ? snapshot.intake.next_question.label_it : snapshot.intake.next_question.label_en}
                    <select
                      value={facts[snapshot.intake.next_question.field] ?? ''}
                      onChange={e => {
                        const field = snapshot.intake.next_question?.field;
                        if (field) setFacts(current => ({ ...current, [field]: e.target.value }));
                      }}
                      disabled={busy}
                    >
                      <option value="">{it ? 'Seleziona una risposta' : 'Select an answer'}</option>
                      {snapshot.intake.next_question.options.map(option => <option
                        key={option.value} value={option.value}>
                        {it ? option.label_it : option.label_en}
                      </option>)}
                    </select>
                  </label>
                  <button type="button" className="button button-primary"
                    disabled={busy || !facts[snapshot.intake.next_question.field]}
                    onClick={() => void run(saveFacts, it ? 'Risposta salvata.' : 'Answer saved.')}>
                    {it ? 'Salva e continua' : 'Save and continue'}
                  </button>
                  {facts[snapshot.intake.next_question.field] === 'unknown' &&
                    <p className="message-box notice">{it
                      ? 'Puoi salvare «Non so», ma la domanda resterà aperta finché non fornisci un dato confermato.'
                      : 'You may save “Not known,” but this question remains open until you provide a confirmed answer.'}</p>}
                </div> : snapshot?.intake?.status === 'outside_first_candidate' ?
                  <p className="message-box notice" role="status">{it
                    ? 'Questo esempio non rientra nel primo scenario proposto. Non significa che la persona non possa presentare una domanda al Comune.'
                    : 'This example is outside the first proposed product scenario. It does not mean the applicant is legally ineligible.'}</p> :
                  snapshot?.intake?.status === 'candidate_scope_complete' ?
                  <p className="message-box notice" role="status">{it
                    ? 'Le risposte corrispondono al primo scenario proposto, ma mancano ancora regole amministrative complete e approvate.'
                    : 'The answers match the first proposed scenario, but a complete approved administrative ruleset is still required.'}</p> :
                  <p>{it ? 'Caricamento delle domande…' : 'Loading guided questions…'}</p>}
                {snapshot?.intake && snapshot.intake.status !== 'needs_information' &&
                  <button type="button" className="button button-outline" disabled={busy}
                    onClick={() => void run(resetScope, it ? 'Domande reimpostate.' : 'Scope questions reset.')}>
                    {it ? 'Modifica le risposte di inquadramento' : 'Change scope answers'}
                  </button>}
              </section>

              <details className={styles.disclosure}>
                <summary>{it ? 'Dati di prova' : 'Fictional test facts'}</summary>
                <p>{it ? 'I campi seguenti sono inventati e non rappresentano criteri legali.' :
                  'The following fields are fictional and do not represent legal eligibility conditions.'}</p>
                <div className={styles.fields}>
                  <label>
                    {it ? 'Esempio di criterio sintetico' : 'Synthetic scenario value'}
                    <select value={facts.synthetic_eligibility}
                      onChange={e => setFacts(x => ({ ...x, synthetic_eligibility: e.target.value }))}
                      disabled={busy}>
                      <option value="">{it ? 'Non specificato' : 'Not provided'}</option>
                      <option value="yes">{it ? 'Sì (solo test)' : 'Yes (test only)'}</option>
                      <option value="no">{it ? 'No (solo test)' : 'No (test only)'}</option>
                    </select>
                  </label>
                  <label>
                    {it ? 'Alloggio fittizio' : 'Fictional housing type'}
                    <select value={facts.housing_arrangement}
                      onChange={e => setFacts(x => ({ ...x, housing_arrangement: e.target.value }))}
                      disabled={busy}>
                      <option value="">{it ? 'Non specificato' : 'Not provided'}</option>
                      <option value="fictional_rental">{it ? 'Locazione fittizia' : 'Fictional rental'}</option>
                      <option value="other">{it ? 'Altro' : 'Other'}</option>
                    </select>
                  </label>
                  <label>
                    {it ? 'Indirizzo inventato' : 'Fictional address'}
                    <input value={facts.property_address} maxLength={180}
                      placeholder="Synthetic Via 10 Milano"
                      onChange={e => setFacts(x => ({ ...x, property_address: e.target.value }))}
                      disabled={busy} />
                  </label>
                  <button type="button" className="button button-primary" disabled={busy}
                    onClick={() => void run(saveFacts, it ? 'Dati di prova salvati.' : 'Test facts saved.')}>
                    {it ? 'Conferma e salva' : 'Confirm and save'}
                  </button>
                </div>
              </details>

              {anprDraft && <details className={styles.disclosure}>
                <summary>{it ? 'Scheda dati ANPR — bozza di preparazione' : 'ANPR worksheet'}</summary>
                <p>{it
                  ? 'Compila solo dati fittizi per questo ambiente. I campi sono tratti da una guida ANPR pubblica la cui corrispondenza con il portale attuale non è ancora confermata. Non è un modulo ufficiale.'
                  : 'Enter fictional test data only. Fields are based on a public ANPR guide that has not been verified against the current portal. This is not an official form.'}</p>
                <p role="status">{it ? 'Stato scheda' : 'Worksheet status'}: <strong>{anprDraft.state.replaceAll('_', ' ')}</strong>
                  {' · '}{it ? 'Campi mancanti' : 'Missing fields'}: {anprDraft.missing_fields.length}</p>
                {anprDraft.sections.map(section => <div key={section.id} style={{ marginTop: 16 }}>
                  <h3>{it ? section.title_it : section.title_en}</h3>
                  <div className={styles.fields}>
                    {section.fields.map(field => <label key={field.key}>
                      {it ? field.label_it : field.label_en}
                      {field.required_in_inspected_guide ? ' *' : ''}
                      {field.input_kind === 'yes_no' ? <select
                        value={facts[field.key] ?? ''}
                        onChange={e => setFacts(v => ({ ...v, [field.key]: e.target.value }))}
                        disabled={busy}
                       >
                        <option value="">{it ? 'Da confermare' : 'Not yet confirmed'}</option>
                        <option value="yes">{it ? 'Sì' : 'Yes'}</option>
                        <option value="no">{it ? 'No' : 'No'}</option>
                      </select> : <input
                        type={field.input_kind === 'date' ? 'date' : 'text'}
                        inputMode={field.input_kind === 'cap' ? 'numeric' : 'text'}
                        value={facts[field.key] ?? ''}
                        maxLength={180} disabled={busy}
                        onChange={e => setFacts(v => ({ ...v, [field.key]: e.target.value }))}
                      />}
                      <small style={{ display: 'block', marginTop: 3 }}>
                        {it ? 'Guida pubblica ANPR' : 'Public ANPR guide'}: {field.guide_page}
                      </small>
                    </label>)}
                  </div>
                </div>)}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 20 }}>
                  <button type="button" className="button button-primary" disabled={busy}
                    onClick={() => void run(saveFacts, it ? 'Campi salvati.' : 'Worksheet facts saved.')}>
                    {it ? 'Salva campi di preparazione' : 'Save preparation fields'}
                  </button>
                  <button type="button" className="button button-outline" disabled={busy}
                    onClick={() => void downloadAnprWorksheet()}>
                    {it ? 'Esporta dati (JSON)' : 'Export data (JSON)'}
                  </button>
                  <button type="button" className="button button-outline" disabled={busy}
                    onClick={() => void downloadAnprWorksheet('txt')}>
                    {it ? 'Scarica riepilogo leggibile' : 'Download readable summary'}
                  </button>
                </div>
                <p style={{ marginTop: 14 }}>
                  <a href={anprDraft.official_handoff.url} target="_blank" rel="noopener noreferrer">
                    {it ? 'Pagina ufficiale del Comune di Milano' : 'Official Comune di Milano residence-change page'}
                  </a>
                </p>
                <p className="message-box notice">{it
                  ? 'Il richiedente deve confermare i dati e inviare la domanda personalmente su ANPR. Non è stato effettuato alcun invio.'
                  : 'The applicant must confirm the information and submit personally through ANPR. No submission has occurred.'}</p>
              </details>}
              </div>

              <div hidden={activeStep !== 'preparation-guide'}>
                <p>{it
                  ? 'Scrivi una domanda fittizia sul prossimo passo, sulle fonti o sullo stato della pratica. Il modello, quando configurato, può scegliere solo strumenti di lettura. Nessuna verifica legale o invio.'
                  : 'Ask a fictional question about your next step, official sources, or saved case status. When configured, the AI model can only select read-only tools. No legal decision or submission.'}</p>
                <label style={{ display: 'block', marginTop: 12 }}>
                  {it ? 'Domanda fittizia' : 'Fictional question'}
                  <textarea rows={2} maxLength={180} value={guideQuestion}
                    placeholder={it ? 'Qual è il prossimo passo?' : 'What should I do next?'}
                    onChange={event => setGuideQuestion(event.target.value)}
                    disabled={guideBusy}
                    />
                </label>
                <button type="button" className="button button-outline" style={{ marginTop: 12 }}
                  disabled={guideBusy || guideQuestion.trim().length < 2}
                  onClick={() => void askGuide()}>
                  {guideBusy ? (it ? 'Controllo…' : 'Checking…') :
                    (it ? 'Chiedi all’assistente' : 'Ask the guide')}
                </button>
                {guideHistory.length > 0 && <div style={{ marginTop: 16 }}>
                  <h3>{it ? 'Conversazione salvata' : 'Saved conversation'}</h3>
                  <p className="account-footnote">{it
                    ? 'Cronologia di prova. Le risposte passate non sostituiscono i dati e le fonti verificati oggi.'
                    : 'Historical preview only. Previous answers do not replace current verified facts or sources.'}</p>
                  <ol>
                    {guideHistory.map(turn => <li key={turn.id} style={{ marginBottom: 12 }}>
                      <p><strong>{turn.question}</strong></p>
                      <p style={{ whiteSpace: 'pre-wrap' }}>{turn.answer}</p>
                      {turn.citation_status === 'unknown' && <p className="account-footnote">{it
                        ? 'La versione della fonte non è registrata per questa risposta.'
                        : 'The source version was not recorded for this answer.'}</p>}
                      {(turn.citation_status === 'historical' || turn.citation_status === 'unavailable') && <p className="account-footnote">{it
                        ? 'Una citazione non è più valida per l’uso attuale. Verifica di nuovo la fonte.'
                        : 'A citation is no longer available for current use. Check the source again.'}</p>}
                      {Boolean(turn.citations?.length) && <ul>
                        {turn.citations?.map(citation => <li key={citation.passage_id}>
                          {citation.source_id} · {it ? 'versione' : 'revision'} {citation.source_revision}
                          {citation.status === 'historical' && (it ? ' · storica' : ' · historical')}
                          <br /><code>{citation.passage_id}</code>
                        </li>)}
                      </ul>}
                    </li>)}
                  </ol>
                </div>}
                {guideResult && <div className="message-box notice" role="status"
                  style={{ marginTop: 16 }}>
                  <p>{guideResult.message}</p>
                  {guideResult.answer_status === 'answer_generated' &&
                    typeof guideResult.answer === 'string' && <div style={{ marginTop: 12 }}>
                      <p><strong>{it ? 'Citazione verificata dalla fonte (in italiano)' :
                        'Verified source quotation (original Italian)'}</strong></p>
                      <p lang="it" style={{ whiteSpace: 'pre-wrap' }}>{guideResult.answer}</p>
                    </div>}
                  <small>{guideResult.mode === 'model_selected'
                    ? (it ? 'Strumento scelto dal modello, dati verificati lato server' :
                      'Model selected the read-only tool; server verified the data')
                    : (it ? 'Strumento di sola lettura scelto con regole; risposta alle fonti con AI se disponibile' :
                      'Read-only tool selected by rules; source answers may use AI')}</small>
                  {guideResult.next_question && <p style={{ marginTop: 8 }}>
                    <strong>{it ? guideResult.next_question.label_it :
                      guideResult.next_question.label_en}</strong>
                  </p>}
                  {(guideResult.blocking_issues ?? []).length > 0 && <p>
                    {it ? 'Blocchi' : 'Blockers'}: {guideResult.blocking_issues?.join(', ')}
                  </p>}
                  {guideResult.references.length > 0 && <ul style={{ marginTop: 8 }}>
                    {guideResult.references.map(ref => <li key={ref.citation_id}>
                      <p lang="it">{ref.excerpt}</p>
                      <a href={ref.official_url} target="_blank" rel="noopener noreferrer">
                        {ref.title}
                      </a>
                    </li>)}
                  </ul>}
                </div>}
              </div>

              <div hidden={activeStep !== 'preparation-evidence'}>
              <section>
                <h3>{it ? 'Regole e lista delle attività' : 'Rules and checklist'}</h3>
                <p>{it ? 'Decisione' : 'Decision'}: <strong>{snapshot?.workflow.rules.decision ?? '—'}</strong></p>
                {(snapshot?.workflow.rules.missing_fields ?? []).length > 0 && <p>
                  {it ? 'Dati mancanti' : 'Missing facts'}: {snapshot?.workflow.rules.missing_fields.join(', ')}
                </p>}
                {(snapshot?.workflow.rules.checklist ?? []).length === 0
                  ? <p>{it ? 'Nessuna lista verificata disponibile. È richiesta la revisione delle fonti ufficiali.' :
                    'No verified checklist available. Official source review is required.'}</p>
                  : <ul>{snapshot?.workflow.rules.checklist.map(item => <li key={item.rule_id}>
                    <strong>{item.description}</strong> — {item.required_document_types.join(', ')}
                    <small style={{ display: 'block' }}>{item.evidence_refs.join(', ')}</small>
                  </li>)}</ul>}
                {(snapshot?.workflow.blocking_issues ?? []).length > 0 &&
                  <p className="message-box notice" role="status">
                    {it ? 'Blocchi' : 'Blockers'}: {snapshot?.workflow.blocking_issues.join(', ')}
                  </p>}
              </section>

              <details className={styles.disclosure}>
                <summary>{it ? 'Fonti ufficiali di riferimento' : 'Official reference passages'}</summary>
                <p>{it
                  ? 'Estratti da fonti approvate per il solo contesto generale. Non equivalgono a una lista personalizzata di obblighi.'
                  : 'Approved-source excerpts for general context only. These are not a personalized checklist or a legal eligibility decision.'}</p>
                {!referenceEvidence || referenceEvidence.references.length === 0
                  ? <p className="message-box notice" role="status">{it
                    ? 'Nessuna fonte verificata disponibile al momento.'
                    : 'No currently verified reference passages are available.'}</p>
                  : <>
                    {referenceEvidence.status !== 'reference_only' &&
                      <p className="message-box notice">{it
                        ? 'Alcune fonti non sono disponibili o sono state revocate.'
                        : 'Some source passages are unavailable or have been revoked.'}</p>}
                    <ul>{referenceEvidence.references.map(ref => <li key={ref.citation_id}
                      style={{ marginTop: 14 }}>
                      <strong>{ref.title}</strong>
                      <p lang="it" style={{ whiteSpace: 'pre-wrap' }}>{ref.excerpt}</p>
                      <a href={ref.official_url} target="_blank" rel="noopener noreferrer">
                        {it ? 'Apri la fonte comunale' : 'Open official municipal source'}
                      </a>
                      <small style={{ display: 'block', marginTop: 4 }}>
                        {it ? 'Revisione' : 'Reviewed'}: {ref.reviewed_at} · {ref.citation_id}
                      </small>
                    </li>)}</ul>
                  </>}
              </details>
              </div>

              <div hidden={activeStep !== 'synthetic-documents'}>
                <div className={styles.documentIntro}><Icon name="file" size={24}/><div>
                  <h3>{it ? 'Aggiungi un file di prova' : 'Add a test file'}</h3>
                <p>{it ? 'PDF o immagini fittizie, max 2 MiB. Le scansioni richiedono OCR disponibile.' :
                  'Fictional PDFs or images, maximum 2 MiB. Scans require an available OCR service.'}</p>
                </div></div>
                {snapshot?.workflow.document_review?.not_legal_validation === true && <div
                  className={styles.documentStatus} role="status" aria-live="polite">
                  <p><strong>{it ? 'Controllo documenti' : 'Document review'}</strong>
                    {' · '}{snapshot.workflow.document_review.document_count}
                    {' '}{it ? 'file' : 'files'}</p>
                  {snapshot.workflow.document_review.conflicts.length > 0 ? <>
                    <p>{it
                      ? 'Sono presenti dati confermati discordanti. Confronta i valori, correggi il campo nella pratica o nel documento e conferma di nuovo prima di procedere.'
                      : 'Confirmed values disagree. Compare them, correct either the saved case fact or the document field, and confirm again before continuing.'}</p>
                    <ul>{snapshot.workflow.document_review.conflicts.map((conflict, index) =>
                      <li key={conflict.kind + ':' + conflict.field + ':' + index}>
                        {conflict.kind === 'cross_document_mismatch'
                          ? (it ? 'Differenza tra documenti' : 'Documents disagree')
                          : (it ? 'Differenza tra pratica e documento' : 'Case and document disagree')}
                        {': '}{conflict.field.replaceAll('_', ' ')}
                      </li>)}</ul>
                  </> : snapshot.workflow.document_review.status === 'verified'
                    ? <p>{it
                      ? 'I dati confermati coincidono. Questo non equivale a un controllo dei requisiti amministrativi.'
                      : 'Confirmed fields agree. This is not a check of administrative requirements.'}</p>
                    : <p>{it
                      ? 'Il controllo dei dati confermati è indipendente dalle regole comunali, ancora soggette a revisione.'
                      : 'Confirmed-value checks are separate from municipal rules, which still require review.'}</p>}
                  {snapshot.workflow.document_review.unreadable.length > 0 &&
                    <p>{it ? 'Documenti illeggibili da sostituire:' : 'Unreadable documents to replace:'}
                      {' '}{snapshot.workflow.document_review.unreadable.length}</p>}
                  {snapshot.workflow.document_review.needs_extraction.length > 0 &&
                    <p>{it ? 'Documenti da estrarre:' : 'Documents needing extraction:'}
                      {' '}{snapshot.workflow.document_review.needs_extraction.length}</p>}
                  {snapshot.workflow.document_review.needs_confirmation.length > 0 &&
                    <p>{it ? 'Documenti con campi da confermare:' : 'Documents with unconfirmed fields:'}
                      {' '}{snapshot.workflow.document_review.needs_confirmation.length}</p>}
                  {snapshot.workflow.document_review.needs_review.length > 0 &&
                    <p>{it ? 'Documenti in attesa di revisione finale:' : 'Documents awaiting final review:'}
                      {' '}{snapshot.workflow.document_review.needs_review.length}</p>}
                </div>}
                <div className={styles.upload}>
                  <details className={styles.disclosure}>
                    <summary>{it ? 'Categoria del file' : 'File category'}</summary>
                    <label>{it ? 'Categoria fittizia' : 'Fictional document category'}
                      <input value={documentType} maxLength={64}
                        onChange={e => setDocumentType(e.target.value)} disabled={busy} />
                    </label>
                  </details>
                  <label>{it ? 'File sintetico' : 'Synthetic file'}
                    <input ref={fileInput} type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                      onChange={e => {
                        setUploadFile(e.currentTarget.files?.[0] ?? null);
                        setError('');
                        setMessage('');
                      }} disabled={busy} aria-invalid={tooLarge}
                      aria-describedby={tooLarge ? 'synthetic-file-size-error' : undefined} />
                  </label>
                  {tooLarge && <p id="synthetic-file-size-error" className={styles.error} role="alert">{it ? 'Seleziona un file di massimo 2 MiB.' : 'Choose a file no larger than 2 MiB.'}</p>}
                  <label className={styles.consent}>
                    <input type="checkbox" checked={syntheticAcknowledged} disabled={busy}
                      onChange={e => setSyntheticAcknowledged(e.target.checked)} />
                    {' '}{it ? 'Confermo che non contiene dati personali reali' :
                      'I confirm that this file contains no real personal information'}
                  </label>
                  <button type="button" className="button button-primary" disabled={
                    busy || !uploadFile || !syntheticAcknowledged || tooLarge
                  } onClick={() => void run(async () => {
                    if (!uploadFile) return;
                    const body = new FormData();
                    body.set('document_type', documentType);
                    body.set('file', uploadFile);
                    const response = await fetch(base + '/documents', {
                      method: 'POST', credentials: 'same-origin', body,
                    });
                    if (!response.ok) throw new PreviewRequestError(response.status);
                    setUploadFile(null);
                    setSyntheticAcknowledged(false);
                    if (fileInput.current) fileInput.current.value = '';
                  }, it ? 'File sintetico caricato.' : 'Synthetic file uploaded.', error =>
                    error instanceof PreviewRequestError && [413, 415, 422].includes(error.status)
                      ? (it ? 'Controlla formato, dimensione e categoria del file.' : 'Check the file format, size and category.')
                      : (it ? 'Caricamento non riuscito. Riprova.' : 'The file could not be uploaded. Try again.'),
                  { kind: 'upload' })}>
                    {it ? 'Carica' : 'Upload'}
                  </button>
                  {documentOperation?.kind === 'upload' &&
                    <DocumentProgress label={it ? 'Caricamento del file…' : 'Uploading file…'} />}
                </div>
                {documents.length > 0 && <h3 className={styles.fileHeading}>{it ? 'File caricati' : 'Uploaded files'}</h3>}
                {message && <p className={styles.success} role="status">{message}</p>}
                {error && <div className={styles.error} role="alert"><Icon name="alert" size={18}/><span>{error}</span></div>}
                {documents.map((doc, index) => <article key={doc.id} className={styles.file}>
                  <h4><Icon name="file" size={18}/>{doc.document_type === 'fictional_agreement'
                    ? (it ? 'Accordo fittizio' : 'Fictional agreement') : doc.document_type.replaceAll('_', ' ')}
                    {' · '}{index + 1}</h4>
                  <p>{doc.status === 'confirmed' ? (it ? 'Revisione confermata' : 'Review confirmed') :
                    doc.extraction_status === 'needs_user_confirmation' ? (it ? 'Campi da confermare' : 'Fields to confirm') :
                    doc.extraction_status === 'unreadable' ? (it ? 'Testo illeggibile' : 'No readable text') :
                    (it ? 'Testo da estrarre' : 'Text extraction pending')}</p>
                  {doc.status !== 'confirmed' &&
                    <button type="button" className="button button-outline" disabled={busy}
                      onClick={() => void run(async () => {
                        await mutate(base + '/documents/' + doc.id + '/extract', 'POST');
                      }, it ? 'Controllo del testo completato.' : 'Text extraction finished.', error =>
                        error instanceof PreviewRequestError && error.status === 503
                          ? (it ? 'Il servizio di estrazione non è disponibile. Il file è salvato. Riprova più tardi.' :
                            'Text extraction is unavailable. Your file is saved. Try again later.')
                          : (it ? 'Impossibile leggere il file. Riprova o scegli un altro documento.' :
                            'The file could not be read. Try again or choose another document.'),
                      { kind: 'extract', id: doc.id })}>
                      {it ? 'Estrai il testo' : 'Extract text'}
                    </button>}
                  {documentOperation?.kind === 'extract' && documentOperation.id === doc.id &&
                    <DocumentProgress label={it ? 'Estrazione del testo…' : 'Extracting text…'} />}
                  {doc.candidates.map((item, i) => {
                    const correctionKey = doc.id + ':' + i;
                    return <div key={correctionKey} style={{ marginTop: 12 }}>
                      <p>{item.field_name}: <strong>{item.raw_value}</strong> ({it ? 'pagina' : 'page'} {item.page})</p>
                      <label>{it ? 'Valore da confermare o correggere' : 'Value to confirm or correct'}
                        <input
                          value={corrections[correctionKey] ?? doc.confirmed_fields[item.field_name] ?? item.raw_value}
                          onChange={e => setCorrections(v => ({ ...v, [correctionKey]: e.target.value }))}
                          disabled={busy} maxLength={180} /></label>
                      <button type="button" className="button button-outline" disabled={busy}
                        onClick={() => void run(async () => {
                          await mutate(base + '/documents/' + doc.id + '/confirm-fields', 'POST', {
                            field_name: item.field_name, raw_value: item.raw_value,
                            page: item.page,
                            confirmed_value: corrections[correctionKey] ??
                              doc.confirmed_fields[item.field_name] ?? item.raw_value,
                          });
                        }, it ? 'Campo confermato.' : 'Field confirmed.')}>
                        {it ? 'Conferma campo' : 'Confirm field'}
                      </button>
                    </div>;
                  })}
                  {doc.extraction_status === 'needs_user_confirmation' && doc.status !== 'confirmed' &&
                    <button type="button" className="button button-primary" style={{ marginTop: 12 }}
                      disabled={busy} onClick={() => void run(async () => {
                        await mutate(base + '/documents/' + doc.id + '/review', 'POST',
                          { confirm_document: true });
                      }, it ? 'Documento verificato.' : 'Document reviewed.')}>
                      {it ? 'Conferma revisione documento' : 'Confirm document review'}
                    </button>}
                  <button type="button" className="button button-outline" style={{ marginTop: 12 }}
                    disabled={busy} onClick={() => {
                      if (!window.confirm(it ? 'Eliminare il file sintetico?' : 'Delete synthetic file?')) return;
                      void run(async () => {
                        await mutate(base + '/documents/' + doc.id, 'DELETE');
                      }, it ? 'File eliminato.' : 'File deleted.');
                    }}>
                    {it ? 'Elimina file' : 'Delete file'}
                  </button>
                </article>)}
              </div>

              <div hidden={activeStep !== 'preparation-package'}>
                {snapshot?.workflow.package ? <>
                  <p>{it ? 'Riepilogo preliminare: non è un modulo ufficiale.' :
                    'Preparation summary: this is not an official application form.'}</p>
                  <details className={styles.disclosure}>
                    <summary>{it ? 'Apri i dati del riepilogo' : 'View summary data'}</summary>
                    <pre className={styles.summaryData}>{JSON.stringify(snapshot.workflow.package.data, null, 2)}</pre>
                  </details>
                  {!snapshot.user_reviewed ? <button className="button button-primary"
                    type="button" disabled={busy} onClick={() => void run(async () => {
                      await mutate(base + '/package/approve', 'POST', {
                        review_digest: snapshot.workflow.package?.review_digest,
                      });
                    }, it ? 'Pacchetto verificato dall’utente.' : 'Package approved by the user.')}>
                    {it ? 'Approva il riepilogo' : 'Approve preparation summary'}
                  </button> : <button className="button button-outline" type="button" disabled={busy}
                    onClick={() => void run(async () => {
                      const response = await fetch(base + '/handoff', { cache: 'no-store' });
                      if (!response.ok) throw new Error('Handoff not available');
                      setHandoff(await response.json() as {
                        links: { title: string; official_url: string }[];
                      });
                    }, it ? 'Fonti ufficiali disponibili.' : 'Official source links available.')}>
                    {it ? 'Visualizza fonti per invio autonomo' : 'View user-only official handoff'}
                  </button>}
                  {snapshot.user_reviewed && <button className="button button-outline"
                    type="button" disabled={busy} style={{ marginLeft: 8 }}
                    onClick={() => void downloadReviewedPackage()}>
                    {it ? 'Scarica il riepilogo verificato (JSON)' :
                      'Download reviewed preparation summary (JSON)'}
                  </button>}
                  {handoff && <ul>{handoff.links.map(link => <li key={link.official_url}>
                    <a href={link.official_url} target="_blank" rel="noopener noreferrer">
                      {link.title}
                    </a>
                  </li>)}</ul>}
                </> : <p>{it ? 'Il riepilogo resta bloccato finché mancano fonti e regole approvate.' :
                  'The package is blocked until approved sources, rules and other prerequisites are present.'}</p>}
              </div>
            </section>
          </div>
        </div>}
    </div>
  </main>;
}
