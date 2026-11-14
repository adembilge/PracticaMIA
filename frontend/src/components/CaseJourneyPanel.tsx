'use client';

import Link from 'next/link';
import {useCallback,useEffect,useRef,useState,type MouseEvent,type ReactNode} from 'react';
import {useDemo} from '@/components/DemoProvider';
import {Icon} from '@/components/Icon';
import {MILAN_OFFICIAL_LINKS} from '@/lib/milan-official-guidance.js';
import {MilanOfficialGuidance} from '@/components/MilanOfficialGuidance';
import {FIRST_ROUTE_SOURCE_LINKS} from '@/lib/approved-source-view.js';
import {PREPARATION_ISSUES} from '@/lib/case-package.js';
import {validCaseWorkflow} from '@/lib/case-workflow.js';

type Evidence={
  citation_id:string;source_id:string;official_url:string;
  title:string;reviewed_at:string;archived_reference:boolean;
};
type Action={
  id:string;status:string;description:string;evidence:Evidence[];
};
type Step={id:string;status:string};
type Workflow={
  case_reference:string;next_action:string;steps:Step[];
  checklist:{
    status:string;items:Action[];reviewed_items:Record<string,string>;
    reviewed_count:number;total:number;fingerprint:string|null;
  };
  package:{
    status:string;download_allowed:boolean;outstanding_issues:string[];
  };
  documents:{enabled:boolean;uploaded_count:number;reviewed_count:number};
};

const copy={
  en:{
    heading:'Your case journey',
    summary:'Current next action',
    intro:'One view of your saved example case. Progress is based on actual case answers and currently approved sources.',
    stages:{
      scope:'Initial questions',intake:'Confirm facts',guidance:'AI explanation',
      checklist:'Review actions',documents:'Review documents',
      package:'Download draft',handoff:'Official handoff',
    },
    state:{
      complete:'Answered',blocked:'Needs attention',needs_attention:'In progress',
      locked:'Available after previous steps',informational:'Optional explanation',
      reviewed_by_user:'Read by you',unavailable:'Not enabled',
      user_reviewed_unverified:'User reviewed, unverified',
      optional_unverified:'No documents reviewed',
      draft_available:'Draft available',user_only_not_submitted:'User submits',
    },
    action:{
      answer_scope:'Answer the next scope question.',
      confirm_intake:'Confirm your saved categorical case facts.',
      consult_official:'This example falls outside the supported route. Consult the official service.',
      review_sources:'The signed checklist is unavailable until the source evidence is approved.',
      review_checklist:'Read each source-backed action and mark it reviewed.',
      resolve_documents:'Resolve the outstanding uploaded-document issues before exporting.',
      download_draft:'You can download a preparation draft; verify official requirements before submission.',
      review_package:'Review outstanding package requirements.',
    },
    rules:'Source-backed actions',
    check:'I have read this action (not completed or submitted)',
    progress:'Actions read by you',
    updated:'Review saved to your case.',
    error:'Unable to update your review. Reload to check current source approvals.',
    loadError:'Unable to load the case workflow. Check your session and try again.',
    loading:'Loading current saved-case progress…',
    refresh:'Refresh workflow',
    archived:'Archived source, not confirmed current',
    source:'Official source',
    package:'Preparation PDF draft',
    draft:'Download PDF draft',
    unavailable:'Package download is blocked until outstanding issues are resolved.',
    issues:'Outstanding issues and limitations',
    noIssues:'No issues found by the limited case checks. This is not legal verification.',
    noDocs:'Real document review is not enabled. Do not upload personal documents.',
    docs:'Open private document review',
    handoff:'Open official ANPR service',
    warning:'Marks record that you read instructions. They are not proof of completion, document authenticity, government acceptance, or submission.',
    note:'The rules are shown in their originally signed English text.',
  },
  it:{
    heading:'Percorso della pratica',
    summary:'Prossima azione',
    intro:'Un unico riepilogo della pratica dimostrativa salvata. Lo stato deriva dalle risposte e dalle fonti attualmente approvate.',
    stages:{
      scope:'Domande iniziali',intake:'Conferma dati',guidance:'Spiegazione AI',
      checklist:'Revisione azioni',documents:'Revisione documenti',
      package:'Scarica bozza',handoff:'Invio ufficiale',
    },
    state:{
      complete:'Risposto',blocked:'Serve attenzione',needs_attention:'In corso',
      locked:'Disponibile dopo i passaggi precedenti',informational:'Spiegazione facoltativa',
      reviewed_by_user:'Letto dall’utente',unavailable:'Non attivo',
      user_reviewed_unverified:'Rivisto, non verificato',
      optional_unverified:'Documenti non verificati',
      draft_available:'Bozza disponibile',user_only_not_submitted:'Invia l’utente',
    },
    action:{
      answer_scope:'Rispondi alla prossima domanda iniziale.',
      confirm_intake:'Conferma i dati categoriali salvati.',
      consult_official:'Questa situazione non è supportata dall’esempio. Consulta il servizio ufficiale.',
      review_sources:'La lista delle azioni non è disponibile finché le fonti non sono approvate.',
      review_checklist:'Leggi le azioni collegate alle fonti e segnale come lette.',
      resolve_documents:'Risolvi i problemi dei documenti prima di esportare.',
      download_draft:'Puoi scaricare una bozza. Verifica i requisiti attuali prima dell’invio.',
      review_package:'Controlla le questioni aperte del riepilogo.',
    },
    rules:'Azioni collegate alle fonti',
    check:'Ho letto questa azione (non completata o inviata)',
    progress:'Azioni lette',
    updated:'Revisione salvata nella pratica.',
    error:'Impossibile aggiornare la revisione. Ricarica le fonti attuali.',
    loadError:'Impossibile caricare il percorso. Controlla l’accesso e riprova.',
    loading:'Caricamento dello stato della pratica…',
    refresh:'Aggiorna percorso',
    archived:'Fonte archiviata, attualità non confermata',
    source:'Fonte ufficiale',
    package:'PDF preparatorio',
    draft:'Scarica la bozza PDF',
    unavailable:'Il download è bloccato finché le questioni aperte non vengono risolte.',
    issues:'Questioni aperte e limitazioni',
    noIssues:'Nessun problema nei controlli limitati. Non è una verifica legale.',
    noDocs:'La revisione di documenti reali non è attiva. Non caricare documenti personali.',
    docs:'Apri la revisione documenti',
    handoff:'Apri il servizio ufficiale ANPR',
    warning:'Questi segni attestano solo la lettura delle istruzioni; non provano completamento, validità, accettazione o invio ufficiale.',
    note:'Le regole sono riportate in inglese nel testo firmato originale.',
  },
} as const;

const stages = ['scope', 'intake', 'checklist', 'documents', 'package'] as const;
type Stage = typeof stages[number];
const anchors: Record<Stage, string> = {
  scope: '#case-scope', intake: '#case-intake', checklist: '#case-workflow-checklist',
  documents: '#case-workflow-documents', package: '#case-workflow-package',
};
const destination: Record<string, Stage> = {
  answer_scope: 'scope', confirm_intake: 'intake', consult_official: 'package',
  review_sources: 'checklist', review_checklist: 'checklist',
  resolve_documents: 'documents', download_draft: 'package', review_package: 'package',
};
const extra = {
  en: {
    nav: 'Case progress', stages: ['Scope', 'Case details', 'Requirements', 'Documents', 'PDF summary'],
    waiting: 'Waiting for confirmed case details.', step: 'Stage', source: 'Requirement and sources', close: 'Close details',
    noFile: 'No private documents have been added.',
    demoDocs: 'Review a fictional document',
    previewDocs: 'Review synthetic documents in Preview',
    demoDocsNotice: 'Use a fictional sample to try document review. Personal-file uploads are unavailable here.',
    completeScope: 'Finish the initial questions first',
    confirmFacts: 'Confirm the case facts first',
    sourcesPending: 'Waiting for approved sources',
    openAssistant: 'Open the evidence assistant',
    draftReady: 'Preparation draft available', draftBlocked: 'Preparation draft blocked',
    manual: 'Submit separately on ANPR', notSent: 'No official submission has been made here.',
    missing: 'Go to the relevant stage', expired: 'Your session has expired.', login: 'Sign in again',
    assistant: 'Help with this case', retry: 'Try again',
    pdfLoading: 'Preparing the PDF…', pdfError: 'The PDF could not be downloaded. Check the current case and try again.',
    officialLink: 'Open ANPR',
  },
  it: {
    nav: 'Avanzamento della pratica', stages: ['Ambito', 'Dati della pratica', 'Requisiti', 'Documenti', 'Riepilogo PDF'],
    waiting: 'In attesa della conferma dei dati della pratica.', step: 'Fase', source: 'Requisito e fonti', close: 'Chiudi dettagli',
    noFile: 'Nessun documento privato aggiunto.',
    demoDocs: 'Esamina un documento di esempio',
    previewDocs: 'Esamina documenti fittizi in anteprima',
    demoDocsNotice: 'Prova la revisione con un documento fittizio. Qui non puoi caricare file personali.',
    completeScope: 'Completa prima le domande iniziali',
    confirmFacts: 'Conferma prima i dati della pratica',
    sourcesPending: 'In attesa delle fonti approvate',
    openAssistant: 'Apri l’assistente con fonti',
    draftReady: 'Bozza di preparazione disponibile', draftBlocked: 'Bozza di preparazione bloccata',
    manual: 'Invia separatamente su ANPR', notSent: 'Da qui non è stato effettuato alcun invio ufficiale.',
    missing: 'Vai alla fase relativa', expired: 'La sessione è scaduta.', login: 'Accedi di nuovo',
    assistant: 'Aiuto per questa pratica', retry: 'Riprova',
    pdfLoading: 'Preparazione del PDF…', pdfError: 'Impossibile scaricare il PDF. Controlla la pratica e riprova.',
    officialLink: 'Apri ANPR',
  },
} as const;

const italianIssues: Record<keyof typeof PREPARATION_ISSUES, string> = {
  checklist_needs_scope: 'Completa le domande iniziali',
  checklist_needs_confirmation: 'Conferma i dati della pratica',
  checklist_outside_first_route: 'Questo esempio non rientra nel percorso supportato',
  checklist_evidence_unavailable: 'Una regola firmata o una fonte ufficiale non è disponibile',
  intake_not_confirmed: 'I dati della pratica non sono confermati',
  intake_data_invalid: 'Non è stato possibile verificare i dati salvati',
  private_document_processing_not_enabled: 'La revisione sicura dei documenti non è attiva',
  document_review_unavailable: 'La revisione dei documenti è temporaneamente indisponibile',
  no_documents_reviewed: 'Non è stato esaminato alcun documento privato',
  document_needs_extraction: 'I dati del documento devono ancora essere estratti',
  document_needs_user_confirmation: 'La revisione del documento non è confermata',
  document_conflict: 'I dati della pratica e del documento non coincidono',
  document_comparison_unresolved: 'Alcuni confronti tra i documenti sono irrisolti',
  document_needs_manual_review: 'Il documento richiede una revisione manuale',
  document_unreadable: 'Un documento caricato è illeggibile',
  document_no_supported_fields: 'Non sono stati trovati campi supportati',
  document_needs_confirmed_intake: 'Conferma i dati della pratica per confrontare il documento',
  document_needs_case_information: 'Manca il dato della pratica corrispondente al campo esaminato',
  document_unsupported_category: 'Categoria non verificata automaticamente',
  document_limit_exceeded: 'Controlla il numero di documenti',
  unscanned_document: 'Manca il risultato della scansione di un documento',
  unrecognized_document_review: 'Non è stato possibile verificare la revisione del documento',
};

function issueStage(issue: string): Stage {
  if (issue === 'checklist_needs_scope') return 'scope';
  if (issue.startsWith('intake_') || issue.includes('case_information') ||
    issue.endsWith('confirmed_intake') || issue === 'checklist_needs_confirmation' ||
    issue === 'checklist_outside_first_route') return 'intake';
  return issue.startsWith('checklist_') ? 'checklist' : 'documents';
}

function RequirementDetails({ item, onClose }: { item: Action | null; onClose: () => void }) {
  const { locale } = useDemo();
  const dialog = useRef<HTMLDialogElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const t = copy[locale];
  const c = extra[locale];

  useEffect(() => {
    const panel = dialog.current;
    if (!panel) return;
    if (!item) {
      if (panel.open) panel.close();
      return;
    }
    const narrow = window.matchMedia('(max-width: 1100px)');
    function sync() {
      if (!panel) return;
      const modal = narrow.matches;
      if (panel.open && panel.matches(':modal') !== modal) panel.close();
      if (!panel.open) {
        if (modal) panel.showModal();
        else panel.show();
      }
      title.current?.focus({ preventScroll: true });
    }
    sync();
    narrow.addEventListener('change', sync);
    return () => narrow.removeEventListener('change', sync);
  }, [item]);

  return <dialog id="case-requirement-detail" className="case-detail" ref={dialog} aria-labelledby="case-detail-title"
    onCancel={event => { event.preventDefault(); onClose(); }}
    onKeyDown={event => { if (event.key === 'Escape' && !dialog.current?.matches(':modal')) onClose(); }}>
    <div className="case-detail-heading">
      <h3 id="case-detail-title" ref={title} tabIndex={-1}>{c.source}</h3>
      <button className="detail-close" type="button" aria-label={c.close} onClick={onClose}><Icon name="x"/></button>
    </div>
    {item && <>
      <p>{item.description}</p>
      <ul>{item.evidence.map(evidence => <li key={evidence.citation_id}>
        <span className="editorial-label">{t.source}</span>
        <a className="editorial-text-link" href={FIRST_ROUTE_SOURCE_LINKS[evidence.source_id as keyof typeof FIRST_ROUTE_SOURCE_LINKS]?.url}
          target="_blank" rel="noopener noreferrer">{evidence.title}<Icon name="external" size={15}/></a>
        <small>{evidence.reviewed_at.slice(0, 10)}{evidence.archived_reference ? ' · ' + t.archived : ''}</small>
      </li>)}</ul>
    </>}
  </dialog>;
}

type JourneyProps = {
  caseId: string;
  refreshKey: number;
  privateDocumentsEnabled: boolean;
  fictionalDocumentsEnabled: boolean;
  preparationEnabled: boolean;
  assistantEnabled: boolean;
  scopeComplete: boolean;
  scope: ReactNode;
  intake: ReactNode;
  sources: ReactNode;
  guidance: ReactNode;
};

export function CaseJourneyPanel({
  caseId, refreshKey, privateDocumentsEnabled, fictionalDocumentsEnabled,
  preparationEnabled, assistantEnabled, scopeComplete, scope, intake, sources, guidance,
}: JourneyProps) {
  const {locale} = useDemo();
  const t = copy[locale];
  const c = extra[locale];
  const [data, setData] = useState<Workflow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<'load' | 'save' | 'expired' | null>(null);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [pdfError, setPdfError] = useState(false);
  const [selection, setSelection] = useState<Stage | null>(null);
  const [direction, setDirection] = useState('forward');
  const [selectedRule, setSelectedRule] = useState<string | null>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const stageHeading = useRef<HTMLHeadingElement>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    setNotice(false);
    try {
      const response = await fetch('/api/cases/' + caseId + '/workflow', {
        credentials: 'same-origin', cache: 'no-store', signal,
      });
      if (response.status === 401) {
        if (!signal?.aborted) { setError('expired'); setData(null); }
        return;
      }
      if (!response.ok) throw new Error('Workflow unavailable');
      const payload: unknown = await response.json();
      if (!validCaseWorkflow(payload)) throw new Error('Invalid workflow');
      if (!signal?.aborted) setData(payload as Workflow);
    } catch {
      if (!signal?.aborted) { setData(null); setError('load'); }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load, refreshKey]);

  const recommendation = scopeComplete || data?.next_action === 'consult_official'
    ? destination[data?.next_action ?? ''] ?? 'intake'
    : 'scope';
  const current = selection ?? (scopeComplete ? recommendation : 'scope');

  useEffect(() => {
    function fromHistory() {
      const hash = window.location.hash;
      setSelection(stages.find(stage => anchors[stage] === hash) ??
        (hash === '#case-handoff' || hash === '#case-workflow-handoff' ? 'package' : hash === '#case-sources' ? 'checklist' : null));
      setSelectedRule(null);
    }
    fromHistory();
    window.addEventListener('popstate', fromHistory);
    window.addEventListener('hashchange', fromHistory);
    return () => {
      window.removeEventListener('popstate', fromHistory);
      window.removeEventListener('hashchange', fromHistory);
    };
  }, []);

  function open(stage: Stage) {
    setSelectedRule(null);
    setDirection(stages.indexOf(stage) < stages.indexOf(current) ? 'back' : 'forward');
    if (window.location.hash !== anchors[stage]) window.history.pushState(null, '', anchors[stage]);
    setSelection(stage);
    requestAnimationFrame(() => stageHeading.current?.focus());
  }

  function closeRule() {
    setSelectedRule(null);
    const button = trigger.current;
    requestAnimationFrame(() => button?.focus());
  }

  async function mark(itemId: string, reviewed: boolean) {
    if (!data?.checklist.fingerprint || saving || loading) return;
    setSelection(current);
    setSaving(true);setError(null);setNotice(false);
    try {
      const response = await fetch('/api/cases/' + caseId + '/workflow/checklist', {
        method: 'PATCH', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({item_id: itemId, reviewed, fingerprint: data.checklist.fingerprint}),
      });
      if (response.status === 401) { setData(null);setError('expired');return; }
      if (!response.ok) {
        await load();
        setError(currentError => currentError ?? 'save');
        return;
      }
      const payload: unknown = await response.json();
      if (!validCaseWorkflow(payload)) throw new Error('Invalid workflow');
      setData(payload as Workflow);
      setNotice(true);
    } catch {
      await load();
      setError(currentError => currentError ?? 'save');
    } finally {setSaving(false);}
  }

  const activeRule = current === 'checklist' ? data?.checklist.items.find(item => item.id === selectedRule) ?? null : null;
  const pdfUrl = '/api/cases/' + encodeURIComponent(caseId) + '/package/pdf';

  async function downloadPdf(event?: MouseEvent<HTMLAnchorElement>) {
    if (event?.altKey || event?.ctrlKey || event?.metaKey || event?.shiftKey) return;
    event?.preventDefault();
    if (pdfBusy || loading || !data?.package.download_allowed) return;
    setSelection('package');setPdfBusy(true);setPdfError(false);
    try {
      const response = await fetch(pdfUrl, {credentials: 'same-origin', cache: 'no-store'});
      if (response.status === 401) { setError('expired');setData(null);return; }
      if (!response.ok || !response.headers.get('content-type')?.startsWith('application/pdf')) {
        if (response.status === 409 || response.status === 404) await load();
        setPdfError(true);
        return;
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = 'practicamia-preparation-draft.pdf';
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    } catch { setPdfError(true); }
    finally { setPdfBusy(false); }
  }

  const caseUrl = '/cases/' + encodeURIComponent(caseId);
  const available = !loading && data?.documents.enabled && privateDocumentsEnabled;
  const showIntake = scopeComplete || current === 'intake';

  return <div className="case-layout">
    <nav className="case-progress" aria-label={c.nav}>
      <p className="editorial-label">{c.nav}</p>
      <ol>{stages.map((stage, index) => {
        const status = data?.steps.find(step => step.id === stage)?.status;
        let target = stage;
        let label: string | undefined = status ? t.state[status as keyof typeof t.state] : undefined;
        if (stage === 'intake' || stage === 'checklist') {
          if (!scopeComplete) { target = 'scope'; label = c.completeScope; }
          else if (stage === 'checklist' && status === 'locked') {
            if (data?.next_action === 'review_sources') label = c.sourcesPending;
            else if (data?.next_action === 'confirm_intake') { target = 'intake'; label = c.confirmFacts; }
          }
        }
        if (stage === 'documents' && !available && !loading) {
          if (fictionalDocumentsEnabled) label = c.demoDocs;
          else if (preparationEnabled) label = c.previewDocs;
        }
        return <li key={stage}><button type="button" aria-current={current === stage ? 'step' : undefined}
          onClick={() => open(target)}>
          <span className="case-step-number">{String(index + 1).padStart(2, '0')}</span>
          <span>{c.stages[index]}{label && <small>{label}</small>}</span>
          {current === stage && <Icon name="arrowRight" size={15}/>}
        </button></li>;
      })}</ol>
    </nav>
    <div className="case-content" data-direction={direction}>
      <div className="case-stage-header">
        <p className="editorial-label">{c.step} {stages.indexOf(current) + 1} / {stages.length}</p>
        <h2 ref={stageHeading} tabIndex={-1}>{c.stages[stages.indexOf(current)]}</h2>
        {data && <div className="case-stage-next">
          <span role="status">{t.action[data.next_action as keyof typeof t.action]}</span>
          {recommendation !== current && <button className="inline-link" type="button" onClick={() => open(recommendation)}>
            {c.stages[stages.indexOf(recommendation)]} →
          </button>}
        </div>}
      </div>
      {loading && <p className="editorial-pending" role="status">{t.loading}</p>}
      {error && <div className="message-box warning case-state" role="alert">
        <Icon name="alert"/><div>
          <p>{error === 'expired' ? c.expired : error === 'save' ? t.error : t.loadError}</p>
          {error === 'expired'
            ? <a className="inline-link" href={'/auth/login?returnTo=' + encodeURIComponent('/cases/' + caseId)}>{c.login}</a>
            : <button type="button" className="inline-link" onClick={() => void load()}>{t.refresh}</button>}
        </div>
      </div>}
      <section className="case-stage" hidden={current !== 'scope'}>{scope}</section>
      {showIntake && <section className="case-stage" hidden={current !== 'intake'}>
        {scopeComplete ? intake : <p className="case-state">{c.waiting}</p>}
      </section>}
      <section className="case-stage" hidden={current !== 'checklist'} id="case-workflow-checklist">
        {data?.checklist.status === 'ready_for_user_review' ? <>
          <div className="case-list-heading"><div><h3>{t.rules}</h3><p>{t.note}</p></div>
            <strong>{t.progress}: {data.checklist.reviewed_count} / {data.checklist.total}</strong></div>
          <ol className="requirement-list">{data.checklist.items.map((item, index) => <li key={item.id}
            data-selected={selectedRule === item.id}>
            <button type="button" className="requirement-open" aria-expanded={selectedRule === item.id}
              aria-controls="case-requirement-detail" onClick={event => { trigger.current = event.currentTarget;setSelectedRule(item.id); }}>
              <span>{String(index + 1).padStart(2, '0')}</span><strong>{item.description}</strong><Icon name="arrowRight" size={17}/>
            </button>
            <label>
              <input type="checkbox" disabled={saving || loading} checked={Object.hasOwn(data.checklist.reviewed_items, item.id)}
                onChange={event => void mark(item.id, event.target.checked)}/>
              {t.check}
            </label>
          </li>)}</ol>
          {notice && <p className="case-confirmation" role="status"><Icon name="check" size={16}/>{t.updated}</p>}
          {saving && <p className="editorial-pending" role="status">{locale === 'it' ? 'Salvataggio…' : 'Saving…'}</p>}
        </> : !loading && <p className="case-state">{data?.next_action === 'review_sources' ? t.action.review_sources : c.waiting}</p>}
        <details className="case-more"><summary>{t.source}</summary>{sources}</details>
      </section>
      <section className="case-stage" hidden={current !== 'documents'} id="case-workflow-documents">
        <div className="case-state"><Icon name="file"/>
          <div><h3>{t.stages.documents}</h3>
            {available ? <>
              <p>{data.documents.uploaded_count ? data.documents.reviewed_count + ' / ' + data.documents.uploaded_count + ' · ' + t.state.user_reviewed_unverified : c.noFile}</p>
              <Link className="button button-primary" href={caseUrl + '/documents'}>{t.docs}<Icon name="arrowRight" size={16}/></Link>
            </> : loading ? <p>{t.loading}</p> : <>
              <p>{fictionalDocumentsEnabled ? c.demoDocsNotice : t.noDocs}</p>
              {fictionalDocumentsEnabled && <Link className="button button-outline" href="/demo/synthetic?step=document">
                {c.demoDocs}<Icon name="arrowRight" size={16}/>
              </Link>}
              {preparationEnabled && <p><Link className="inline-link" href={caseUrl + '/preparation#synthetic-documents'}>{c.previewDocs} →</Link></p>}
            </>}
          </div>
        </div>
      </section>
      <section className="case-stage" hidden={current !== 'package'} id="case-workflow-package">
        {data && <div className="package-sheet">
          <div className="package-sheet-title"><Icon name="file" size={28}/><div><h3>{t.package}</h3>
            <p>{data.package.download_allowed ? c.draftReady : c.draftBlocked}</p></div></div>
          {data.package.outstanding_issues.length > 0 && <ul className="package-issues">
            {data.package.outstanding_issues.map(issue => {
              const key = issue as keyof typeof PREPARATION_ISSUES;
              const stage = issueStage(issue);
              const actionable = !data.package.download_allowed && (stage !== 'documents' || available) && stage !== current;
              return <li key={issue}><span>{(locale === 'it' ? italianIssues : PREPARATION_ISSUES)[key] ?? issue}</span>
                {actionable && <button className="inline-link" type="button" onClick={() => open(stage)}>{c.missing} →</button>}
              </li>;
            })}
          </ul>}
          {!data.package.download_allowed && <p className="case-state">{t.unavailable}</p>}
          {data.package.download_allowed && !loading && <a className="button button-primary"
            href={pdfUrl} onClick={downloadPdf} aria-disabled={pdfBusy}>{t.draft}<Icon name="arrowRight" size={17}/></a>}
          {pdfBusy && <p className="editorial-pending" role="status">{c.pdfLoading}</p>}
          {pdfError && <div className="message-box warning" role="alert"><div><p>{c.pdfError}</p>
            {data.package.download_allowed && <button className="inline-link" type="button" disabled={pdfBusy || loading}
              onClick={() => void downloadPdf()}>{c.retry}</button>}
          </div></div>}
        </div>}
        <div className="case-handoff" id="case-handoff">
          <h3>{c.manual}</h3><p>{c.notSent}</p>
          <a className="editorial-text-link" href={MILAN_OFFICIAL_LINKS.anpr} target="_blank" rel="noopener noreferrer">
            {c.officialLink}<Icon name="external" size={16}/>
          </a>
          {scopeComplete && <details className="case-more"><summary>{t.source}</summary><MilanOfficialGuidance locale={locale}/></details>}
        </div>
      </section>
      {(guidance || assistantEnabled) && <details className="case-more"><summary>{c.assistant}</summary>
        {assistantEnabled && <p><Link className="inline-link" href={caseUrl + '/assistant'}>{c.openAssistant} →</Link></p>}
        {guidance}
      </details>}
      {data && !error && <button className="inline-link workflow-refresh" type="button" disabled={loading || saving}
        onClick={() => void load()}>{t.refresh}</button>}
    </div>
    <RequirementDetails item={activeRule} onClose={closeRule}/>
  </div>;
}
