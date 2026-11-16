'use client';

import Link from 'next/link';
import {useCallback, useEffect, useState} from 'react';
import {useDemo} from '@/components/DemoProvider';
import {Icon} from '@/components/Icon';
import {DocumentProgress} from '@/components/DocumentProgress';
import {PrivateDocumentIntelligence} from '@/components/PrivateDocumentIntelligence';
import {
  PRIVATE_DOCUMENT_CONSENT_VERSION,
  PRIVATE_DOCUMENT_MAX_BYTES,
} from '@/lib/private-documents.js';

type Doc = {
  id: string;
  category: string;
  media_type: string;
  uploaded_at: string;
  expires_at: string;
  review_status: 'stored_unverified';
  official_submission: false;
};
type Props = {caseId: string; configured: boolean; signedIn: boolean; fixtureMode?: boolean};

const messages = {
  en: {
    title: 'Private documents',
    lead: 'Encrypted temporary storage for documents you choose to organize. Upload does not verify your documents, determine your eligibility or submit anything to ANPR.',
    signIn: 'Sign in to use your private document vault.',
    unavailable: 'Private document storage is not available.',
    category: 'Document category (for organization only)',
    housing_document: 'Housing document',
    identity_document: 'Identity document',
    other_supporting_document: 'Other supporting document',
    choose: 'Choose a PDF, PNG or JPEG (maximum 2 MiB)',
    categoryNote: 'Only housing documents support automated field extraction. Other categories remain unverified and may appear as warnings in a draft.',
    consent: 'I have read the document privacy notice. I understand the document is scanned, encrypted and accessible only to my account, expires after seven days, and may remain temporarily in infrastructure backups.',
    privacy: 'Read the document privacy notice',
    upload: 'Upload securely',
    uploading: 'Scanning and encrypting…',
    stored: 'Stored files (not legally verified)',
    empty: 'No active documents in this case.',
    expires: 'Access expires',
    delete: 'Delete now',
    confirmDelete: 'Delete this document immediately from active storage?',
    failed: 'The operation failed. Your document may not have been saved. Please try again.',
    sizeError: 'The file is empty or exceeds 2 MiB.',
    refresh: 'Refresh documents',
    back: 'Back to case',
    note: 'Automatic deletion is scheduled after expiry. Infrastructure backup copies may persist according to the provider retention period. No document content is sent to an LLM.',
  },
  it: {
    title: 'Documenti privati',
    lead: 'Archivio temporaneo cifrato per organizzare documenti. Il caricamento non verifica la validità legale, i requisiti né presenta pratiche ad ANPR.',
    signIn: 'Accedi per usare l’archivio.',
    unavailable: 'Archivio documenti privati non disponibile.',
    category: 'Categoria (solo per organizzazione)',
    housing_document: 'Documento relativo all’alloggio',
    identity_document: 'Documento di identità',
    other_supporting_document: 'Altro documento',
    choose: 'Scegli PDF, PNG o JPEG (massimo 2 MiB)',
    categoryNote: 'Solo i documenti dell’alloggio supportano l’estrazione automatica. Le altre categorie restano non verificate e possono comparire come avvisi nel PDF.',
    consent: 'Ho letto l’informativa sui documenti. Comprendo che il file viene analizzato, cifrato, accessibile solo al mio account, scade dopo sette giorni e potrebbe restare temporaneamente nei backup.',
    privacy: 'Leggi l’informativa sui documenti',
    upload: 'Carica in modo sicuro',
    uploading: 'Analisi e cifratura…',
    stored: 'File conservati (non verificati legalmente)',
    empty: 'Non ci sono documenti attivi per questa pratica.',
    expires: 'Accesso fino al',
    delete: 'Elimina subito',
    confirmDelete: 'Eliminare subito il documento dall’archivio attivo?',
    failed: 'Operazione non riuscita. Riprova.',
    sizeError: 'Il file è vuoto o supera 2 MiB.',
    refresh: 'Aggiorna documenti',
    back: 'Torna alla pratica',
    note: 'La cancellazione automatica è programmata dopo la scadenza. Copie nei backup potrebbero persistere secondo i tempi del fornitore. Il contenuto non viene inviato a un LLM.',
  },
} as const;

export function PrivateDocumentsWorkspace({caseId, configured, signedIn, fixtureMode = false}: Props) {
  const {locale} = useDemo();
  const t = messages[locale];
  const [docs,setDocs] = useState<Doc[]>([]);
  const [category,setCategory] = useState('housing_document');
  const [file,setFile] = useState<File|null>(null);
  const [agreed,setAgreed] = useState(false);
  const [operation,setOperation] = useState<'upload'|'delete'|null>(null);
  const busy = operation !== null;
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState('');
  const [notice,setNotice] = useState('');
  const [expired,setExpired] = useState(false);
  const [failure,setFailure] = useState<'load'|'upload'|'delete'|null>(null);
  const [selection,setSelection] = useState<string|null>(null);
  const selected = docs.find(doc => doc.id === selection) ?? docs[0];
  const back = '/cases/' + encodeURIComponent(caseId);
  const login = '/auth/login?returnTo=' + encodeURIComponent(back + '/documents');
  const it = locale === 'it';
  const uploadLabel = it ? 'Aggiungi un documento' : 'Add a document';
  const fileInvalid = Boolean(file && (file.size < 1 || file.size > PRIVATE_DOCUMENT_MAX_BYTES));
  const wrongType = Boolean(file?.type && !['application/pdf','image/png','image/jpeg'].includes(file.type));
  const invalidMessage = it ? 'Il file non è un PDF, PNG o JPEG valido.' : 'Choose a valid PDF, PNG or JPEG file.';
  const retry = it ? 'Riprova' : 'Try again';

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);setError('');setFailure(null);
    try {
      const r = await fetch('/api/cases/' + caseId + '/private-documents', {
        credentials: 'same-origin', cache: 'no-store', signal,
      });
      if (r.status === 401) { if (!signal?.aborted) setExpired(true);return; }
      if (!r.ok) throw new Error('Unavailable');
      const data: unknown = await r.json();
      if (!Array.isArray(data)) throw new Error('Malformed response');
      if (!signal?.aborted) {setDocs(data as Doc[]);setExpired(false);}
    } catch {
      if (!signal?.aborted) {setError(messages[locale].failed);setFailure('load');}
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [caseId,locale]);
  useEffect(() => {
    if (!configured || !signedIn) {setLoading(false); return;}
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [configured, signedIn, load]);

  async function upload() {
    if (!file || !agreed || busy || expired || fileInvalid || wrongType) return;
    setOperation('upload');setError('');setNotice('');setFailure(null);
    const form = new FormData();
    form.set('file',file);
    form.set('category',category);
    form.set('privacy_ack','true');
    form.set('consent_version',PRIVATE_DOCUMENT_CONSENT_VERSION);
    try {
      const r = await fetch('/api/cases/' + caseId + '/private-documents',{
        method:'POST',credentials:'same-origin',body:form,
      });
      if (r.status === 401) {setExpired(true);return;}
      if (r.status === 429) {
        setError(it ? 'La pratica ha raggiunto il limite di documenti. Rimuovi un file per continuare.' :
          'This case has reached its document limit. Remove a file to continue.');
        return;
      }
      if ([400, 413, 415, 422].includes(r.status)) {
        setError(r.status === 413 ? t.sizeError : it ?
          'Il controllo del file non è riuscito. Seleziona un altro documento e riprova.' :
          'The file did not pass the upload checks. Choose another document and try again.');
        return;
      }
      if (!r.ok) throw new Error('Upload failed');
      const uploaded = await r.json().catch(() => null) as Doc | null;
      if (uploaded?.id) setSelection(uploaded.id);
      setNotice(it ? 'Documento salvato.' : 'Document saved.');
      setFile(null);setAgreed(false);
      const input = document.getElementById('private-document-file') as HTMLInputElement|null;
      if (input) input.value = '';
      await load();
    } catch {setError(t.failed);setFailure('upload');}
    finally {setOperation(null);}
  }

  async function erase(id:string) {
    if (busy || !window.confirm(t.confirmDelete)) return;
    setOperation('delete');setError('');setNotice('');setFailure(null);
    try {
      const r = await fetch('/api/cases/' + caseId + '/private-documents/' + id,{
        method:'DELETE',credentials:'same-origin',
      });
      if (r.status === 401) {setExpired(true);return;}
      if (r.status !== 204) throw new Error('Delete failed');
      await load();
    } catch {setError(t.failed);setFailure('delete');}
    finally {setOperation(null);}
  }

  return <main className="case-page document-page" id="main-content" tabIndex={-1}>
    <div className="container">
      <header className="case-header">
        <div><p className="editorial-label">{it ? 'Pratica · Documenti' : 'Case file · Documents'}</p>
          <h1>{t.title}</h1></div>
        <Link className="editorial-text-link" href={back + '#case-workflow-documents'}>← {t.back}</Link>
      </header>
      <p className="document-lead">{fixtureMode
        ? (it ? 'Ambiente di prova. Carica solo i file di alloggio fittizi forniti per il test.'
              : 'Test environment. Use only the fictional housing files provided for this test.')
        : t.lead}</p>
      {(!signedIn || expired) && configured && <div className="message-box warning" role="alert">
        <div><p>{expired ? (it ? 'La sessione è scaduta.' : 'Your session has expired.') : t.signIn}</p>
          <a className="inline-link" href={login}>{it ? 'Accedi' : 'Sign in'}</a></div>
      </div>}
      {!configured && <p className="case-state">{t.unavailable}</p>}
      {configured && signedIn && !expired && <div className="documents-layout">
        <aside className="document-nav" aria-label={t.stored}>
          <h2>{t.stored}</h2>
          {loading && <p className="editorial-pending" role="status">{it ? 'Caricamento…' : 'Loading…'}</p>}
          {!loading && !error && !docs.length && <p>{t.empty}</p>}
          {docs.map((doc, index) => <button key={doc.id} type="button" aria-pressed={selected?.id === doc.id}
            onClick={() => setSelection(doc.id)} disabled={busy}>
            <Icon name="file" size={18}/><span>{t[doc.category as keyof typeof t] || doc.category}<small>File {index + 1}</small></span>
          </button>)}
          <button type="button" className="inline-link" disabled={busy || loading} onClick={() => void load()}>{t.refresh}</button>
        </aside>
        <div className="documents-main">
          {selected && <section className="document-card">
            <div className="document-card-heading"><div>
              <h2>{t[selected.category as keyof typeof t] || selected.category}</h2>
              <p>{t.expires} {new Date(selected.expires_at).toLocaleDateString(it ? 'it-IT' : 'en-GB')}</p>
            </div><button type="button" disabled={busy || loading} className="button button-outline"
              onClick={() => void erase(selected.id)}>{t.delete}</button></div>
            {selected.category === 'housing_document' && <PrivateDocumentIntelligence key={selected.id} caseId={caseId} documentId={selected.id}/>}
            {failure === 'delete' && <div className="message-box warning" role="alert"><div><p>{error}</p>
              <button type="button" className="inline-link" onClick={() => void erase(selected.id)}>{retry}</button></div></div>}
          </section>}
          {failure === 'load' && <div className="message-box warning" role="alert"><div><p>{error}</p>
            <button type="button" className="inline-link" onClick={() => void load()}>{retry}</button>
          </div></div>}
          <form className="document-card document-upload" onSubmit={event => {event.preventDefault();void upload();}}>
            <h2>{uploadLabel}</h2>
            <label htmlFor="private-document-category" className="field-label">{t.category}</label>
            <select className="input" id="private-document-category" disabled={busy}
              value={category} onChange={e => setCategory(e.target.value)}>
              <option value="housing_document">{t.housing_document}</option>
              {!fixtureMode && <option value="identity_document">{t.identity_document}</option>}
              {!fixtureMode && <option value="other_supporting_document">{t.other_supporting_document}</option>}
            </select>
            <p>{t.categoryNote}</p>
            <label htmlFor="private-document-file" className="field-label">{t.choose}</label>
            <input id="private-document-file" type="file" disabled={busy} accept="application/pdf,image/png,image/jpeg"
              onChange={e => {setFile(e.target.files?.[0] ?? null);setError('');setFailure(null);setNotice('');}}
              aria-invalid={fileInvalid || wrongType || (Boolean(error) && failure === null)}
              aria-describedby={fileInvalid || wrongType || (error && (!failure || failure === 'upload')) ? 'document-upload-error' : undefined}/>
            {(fileInvalid || wrongType || (error && (!failure || failure === 'upload'))) &&
              <div className="message-box warning" id="document-upload-error" role="alert"><div>
                <p>{fileInvalid ? t.sizeError : wrongType ? invalidMessage : error}</p>
                {failure === 'upload' && <button type="button" className="inline-link" onClick={() => void upload()}>{retry}</button>}
              </div></div>}
            <p><Link href="/privacy/documents" className="inline-link" target="_blank">{t.privacy}</Link></p>
            <label className="document-consent">
              <input type="checkbox" disabled={busy} checked={agreed} onChange={e => setAgreed(e.target.checked)}/>
              <span>{t.consent}</span>
            </label>
            <button className="button button-primary" type="submit" disabled={busy || !file || !agreed || fileInvalid || wrongType}>{t.upload}</button>
            {operation === 'upload' && <DocumentProgress label={t.uploading}/>}
            {notice && <p className="case-confirmation" role="status">{notice}</p>}
          </form>
          <p className="document-lead">{t.note}</p>
        </div>
      </div>}
    </div>
  </main>;
}
