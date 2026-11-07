'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { useDemo } from '@/components/DemoProvider';

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
type Assessment = {
  status: string;
  next_action: string;
  blocking_issues: string[];
  rules: {
    decision: string;
    missing_fields: string[];
    evidence_refs: string[];
    checklist: ChecklistItem[];
  };
  package: PackageData | null;
};
type ScopeField = 'citizenship_class' | 'registration_context' | 'destination_municipality' | 'household_scope';
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
type Props = { caseId: string; signedIn: boolean; configured: boolean };

export function PreparationPreview({ caseId, signedIn, configured }: Props) {
  const { locale } = useDemo();
  const it = locale === 'it';
  const base = '/api/cases/' + encodeURIComponent(caseId) + '/preparation';
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [referenceEvidence, setReferenceEvidence] = useState<ReferenceEvidence | null>(null);
  const [facts, setFacts] = useState({
    citizenship_class: '',
    registration_context: '',
    destination_municipality: '',
    household_scope: '',
    synthetic_eligibility: '',
    housing_arrangement: '',
    property_address: '',
  });
  const [documentType, setDocumentType] = useState('fictional_agreement');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [syntheticAcknowledged, setSyntheticAcknowledged] = useState(false);
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [handoff, setHandoff] = useState<{ links: { title: string; official_url: string }[] } | null>(null);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const [state, docs, sources] = await Promise.all([
      fetch(base, { cache: 'no-store', signal }),
      fetch(base + '/documents', { cache: 'no-store', signal }),
      fetch(base + '/reference-evidence', { cache: 'no-store', signal })
        .catch(() => null),
    ]);
    if (!state.ok || !docs.ok) throw new Error('Preview service unavailable');
    const saved = await state.json() as Snapshot;
    const list = await docs.json() as DocumentSummary[];
    if (!saved.is_demo || !saved.intake || saved.intake.is_legal_assessment !== false ||
      !Array.isArray(list)) throw new Error('Invalid preview data');
    setSnapshot(saved);
    setDocuments(list);
    // Reference evidence is optional; retrieval failures must not break
    // the private case workspace or silently invent a citation.
    if (sources?.ok) {
      const evidence = await sources.json() as ReferenceEvidence;
      setReferenceEvidence(
        evidence?.is_demo && evidence.personalized_requirements === false &&
        Array.isArray(evidence.references) ? evidence : null,
      );
    } else {
      setReferenceEvidence(null);
    }
    setFacts({
      citizenship_class: String(saved.confirmed_facts.citizenship_class ?? ''),
      registration_context: String(saved.confirmed_facts.registration_context ?? ''),
      destination_municipality: String(saved.confirmed_facts.destination_municipality ?? ''),
      household_scope: String(saved.confirmed_facts.household_scope ?? ''),
      synthetic_eligibility: String(saved.confirmed_facts.synthetic_eligibility ?? ''),
      housing_arrangement: String(saved.confirmed_facts.housing_arrangement ?? ''),
      property_address: String(saved.confirmed_facts.property_address ?? ''),
    });
  }, [base]);

  useEffect(() => {
    if (!configured || !signedIn) return;
    const controller = new AbortController();
    void refresh(controller.signal).catch(() => {
      if (!controller.signal.aborted) setError(
        it ? 'Impossibile caricare questa anteprima.' : 'Could not load this preview.',
      );
    });
    return () => controller.abort();
  }, [configured, signedIn, refresh, it]);

  async function mutate(url: string, method: string, body?: unknown): Promise<unknown> {
    const response = await fetch(url, {
      method,
      credentials: 'same-origin',
      ...(body !== undefined ? {
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      } : {}),
    });
    if (!response.ok) throw new Error('Operation rejected: ' + response.status);
    if (response.status === 204) return null;
    return response.json() as Promise<unknown>;
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
      'destination_municipality', 'household_scope']) {
      delete confirmed_facts[field];
    }
    await mutate(base + '/facts', 'PUT', { confirmed_facts });
  }

  async function run(action: () => Promise<void>, success: string) {
    setBusy(true);
    setError('');
    setMessage('');
    setHandoff(null);
    try {
      await action();
      await refresh();
      setMessage(success);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview operation failed');
    } finally {
      setBusy(false);
    }
  }

  if (!configured || !signedIn) return (
    <main id="main-content" className="subpage-background">
      <div className="container account-shell">
        <h1>{it ? 'Anteprima preparazione' : 'Preparation preview'}</h1>
        <p>{it ? 'È necessario effettuare l’accesso alla configurazione di test.' :
          'Sign in to the configured test environment.'}</p>
        <a href="/auth/login" className="button button-primary">{it ? 'Accedi' : 'Sign in'}</a>
      </div>
    </main>
  );

  return <main className="workspace-page" id="main-content">
    <div className="container workspace-head">
      <div>
        <span className="tiny-eyebrow">{it ? 'Solo ambiente di test' : 'Test environment only'}</span>
        <h1>{it ? 'Preparazione della pratica' : 'Case preparation'}</h1>
        <p>{it ? 'Solo dati sintetici. Nessun requisito legale è stato approvato.' :
          'Synthetic data only. No Milan administrative rules have been approved.'}</p>
      </div>
      <Link className="exit-link" href={'/cases/' + encodeURIComponent(caseId)}>
        {it ? 'Torna alla pratica' : 'Back to case'}
      </Link>
    </div>

    <div className="container" style={{ marginTop: 24, paddingBottom: 60, maxWidth: 970 }}>
      <div className="message-box warning" role="alert">
        <div><strong>{it ? 'Non inserire dati reali.' : 'Do not enter real personal information.'}</strong>
          <p>{it ? 'Non caricare contratti, documenti di identità o indirizzi reali.' :
            'Do not upload genuine contracts, identity documents or real addresses.'}</p></div>
      </div>
      {message && <p role="status" className="message-box notice">{message}</p>}
      {error && <p role="alert" className="error-text">{error}</p>}

      <section className="work-panel" style={{ padding: 24, marginTop: 20 }} aria-busy={busy}>
        <h2>{it ? '0. Domande guidate per il caso' : '0. Guided case intake'}</h2>
        <p>{it
          ? 'Queste domande verificano soltanto se un caso fittizio corrisponde al primo scenario proposto. Non determinano diritti o requisiti legali.'
          : 'These questions only check whether a fictional case matches the first proposed product scenario. They do not determine legal eligibility or requirements.'}</p>
        {snapshot?.intake && <p aria-live="polite">
          {it ? 'Risposte di inquadramento' : 'Scope answers'}: {snapshot.intake.answered_count} / {snapshot.intake.total_questions}
        </p>}
        {snapshot?.intake?.next_question ? <div style={{ display: 'grid', gap: 12, maxWidth: 620 }}>
          <label>
            {it ? snapshot.intake.next_question.label_it : snapshot.intake.next_question.label_en}
            <select
              value={facts[snapshot.intake.next_question.field]}
              onChange={e => {
                const field = snapshot.intake.next_question?.field;
                if (field) setFacts(current => ({ ...current, [field]: e.target.value }));
              }}
              disabled={busy}
              style={{ display: 'block', width: '100%', padding: 12, marginTop: 8 }}
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

      <section className="work-panel" style={{ padding: 24, marginTop: 20 }} aria-busy={busy}>
        <h2>{it ? '1. Dati di prova confermati' : '1. Confirmed test facts'}</h2>
        <p>{it ? 'I campi seguenti sono inventati e non rappresentano criteri legali.' :
          'The following fields are fictional and do not represent legal eligibility conditions.'}</p>
        <div style={{ display: 'grid', gap: 12, marginTop: 18 }}>
          <label>
            {it ? 'Esempio di criterio sintetico' : 'Synthetic scenario value'}
            <select value={facts.synthetic_eligibility}
              onChange={e => setFacts(x => ({ ...x, synthetic_eligibility: e.target.value }))}
              disabled={busy} style={{ display: 'block', width: '100%', padding: 12 }}>
              <option value="">{it ? 'Non specificato' : 'Not provided'}</option>
              <option value="yes">{it ? 'Sì (solo test)' : 'Yes (test only)'}</option>
              <option value="no">{it ? 'No (solo test)' : 'No (test only)'}</option>
            </select>
          </label>
          <label>
            {it ? 'Alloggio fittizio' : 'Fictional housing type'}
            <select value={facts.housing_arrangement}
              onChange={e => setFacts(x => ({ ...x, housing_arrangement: e.target.value }))}
              disabled={busy} style={{ display: 'block', width: '100%', padding: 12 }}>
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
              disabled={busy} style={{ display: 'block', width: '100%', padding: 12 }} />
          </label>
          <button type="button" className="button button-primary" disabled={busy}
            onClick={() => void run(saveFacts, it ? 'Dati di prova salvati.' : 'Test facts saved.')}>
            {it ? 'Conferma e salva' : 'Confirm and save'}
          </button>
        </div>
      </section>

      <section className="work-panel" style={{ padding: 24, marginTop: 20 }}>
        <h2>{it ? '2. Regole e lista delle attività' : '2. Rules and checklist'}</h2>
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

      <section className="work-panel" style={{ padding: 24, marginTop: 20 }}>
        <h2>{it ? '2a. Fonti ufficiali di riferimento' : '2a. Official reference passages'}</h2>
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
      </section>

      <section className="work-panel" style={{ padding: 24, marginTop: 20 }}>
        <h2>{it ? '3. Documenti sintetici' : '3. Synthetic documents'}</h2>
        <p>{it ? 'PDF o immagini fittizie, max 2 MiB. Le scansioni richiedono OCR disponibile.' :
          'Fictional PDFs or images, maximum 2 MiB. Scans require an available OCR service.'}</p>
        <div style={{ display: 'grid', gap: 12, maxWidth: 620 }}>
          <label>{it ? 'Categoria fittizia' : 'Fictional document category'}
            <input value={documentType} maxLength={64}
              onChange={e => setDocumentType(e.target.value)} disabled={busy}
              style={{ display: 'block', width: '100%', padding: 12 }} /></label>
          <label>{it ? 'File sintetico' : 'Synthetic file'}
            <input type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
              onChange={e => setUploadFile(e.currentTarget.files?.[0] ?? null)}
              disabled={busy} style={{ display: 'block', marginTop: 8 }} /></label>
          <label>
            <input type="checkbox" checked={syntheticAcknowledged} disabled={busy}
              onChange={e => setSyntheticAcknowledged(e.target.checked)} />
            {' '}{it ? 'Confermo che non contiene dati personali reali' :
              'I confirm that this file contains no real personal information'}
          </label>
          <button type="button" className="button button-primary" disabled={
            busy || !uploadFile || !syntheticAcknowledged ||
            uploadFile.size > 2 * 1024 * 1024
          } onClick={() => void run(async () => {
            if (!uploadFile) return;
            const body = new FormData();
            body.set('document_type', documentType);
            body.set('file', uploadFile);
            const response = await fetch(base + '/documents', {
              method: 'POST', credentials: 'same-origin', body,
            });
            if (!response.ok) throw new Error('Upload rejected: ' + response.status);
            setUploadFile(null);
            setSyntheticAcknowledged(false);
          }, it ? 'File sintetico caricato.' : 'Synthetic file uploaded.')}>
            {it ? 'Carica' : 'Upload'}
          </button>
        </div>
        {documents.map(doc => <article key={doc.id} style={{
          borderTop: '1px solid var(--border, #aaa)', marginTop: 20, paddingTop: 16,
        }}>
          <p><strong>{doc.document_type}</strong> — {doc.status}</p>
          <p>{it ? 'Estrazione' : 'Extraction'}: {doc.extraction_status}</p>
          {doc.status !== 'confirmed' &&
            <button type="button" className="button button-outline" disabled={busy}
              onClick={() => void run(async () => {
                await mutate(base + '/documents/' + doc.id + '/extract', 'POST');
              }, it ? 'Estrazione completata.' : 'Extraction processed.')}>
              {it ? 'Estrai il testo' : 'Extract text'}
            </button>}
          {doc.candidates.map((item, i) => {
            const correctionKey = doc.id + ':' + i;
            return <div key={correctionKey} style={{ marginTop: 12 }}>
              <p>{item.field_name}: <strong>{item.raw_value}</strong> ({it ? 'pagina' : 'page'} {item.page})</p>
              <label>{it ? 'Valore da confermare o correggere' : 'Value to confirm or correct'}
                <input style={{ display: 'block', width: '100%', padding: 10 }}
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
            disabled={busy} onClick={() => void run(async () => {
              if (!window.confirm(it ? 'Eliminare il file sintetico?' : 'Delete synthetic file?')) return;
              await mutate(base + '/documents/' + doc.id, 'DELETE');
            }, it ? 'File eliminato.' : 'File deleted.')}>
            {it ? 'Elimina file' : 'Delete file'}
          </button>
        </article>)}
      </section>

      <section className="work-panel" style={{ padding: 24, marginTop: 20 }}>
        <h2>{it ? '4. Pacchetto per revisione' : '4. Reviewable preparation package'}</h2>
        <p>{it ? 'Stato' : 'Status'}: <strong>{snapshot?.workflow.status ?? '—'}</strong></p>
        {snapshot?.workflow.package ? <>
          <p>{it ? 'Riepilogo preliminare: non è un modulo ufficiale.' :
            'Preparation summary: this is not an official application form.'}</p>
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', fontSize: 12 }}>
            {JSON.stringify(snapshot.workflow.package.data, null, 2)}
          </pre>
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
          {handoff && <ul>{handoff.links.map(link => <li key={link.official_url}>
            <a href={link.official_url} target="_blank" rel="noopener noreferrer">
              {link.title}
            </a>
          </li>)}</ul>}
        </> : <p>{it ? 'Il riepilogo resta bloccato finché mancano fonti e regole approvate.' :
          'The package is blocked until approved sources, rules and other prerequisites are present.'}</p>}
      </section>
    </div>
  </main>;
}
