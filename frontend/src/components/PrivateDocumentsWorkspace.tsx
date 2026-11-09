'use client';

import Link from 'next/link';
import {useCallback, useEffect, useState} from 'react';
import {useDemo} from '@/components/DemoProvider';
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
type Props = {caseId: string; configured: boolean; signedIn: boolean};

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

export function PrivateDocumentsWorkspace({caseId, configured, signedIn}: Props) {
  const {locale} = useDemo();
  const t = messages[locale];
  const [docs,setDocs] = useState<Doc[]>([]);
  const [category,setCategory] = useState('housing_document');
  const [file,setFile] = useState<File|null>(null);
  const [agreed,setAgreed] = useState(false);
  const [busy,setBusy] = useState(false);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState('');

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    try {
      const r = await fetch('/api/cases/' + caseId + '/private-documents', {
        credentials: 'same-origin', cache: 'no-store', signal,
      });
      if (!r.ok) throw new Error('Unavailable');
      const data: unknown = await r.json();
      if (!Array.isArray(data)) throw new Error('Malformed response');
      if (!signal?.aborted) setDocs(data as Doc[]);
    } catch {
      if (!signal?.aborted) setError(messages[locale].failed);
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
    if (!file || !agreed || busy || file.size < 1 || file.size > PRIVATE_DOCUMENT_MAX_BYTES) {
      if (file && (file.size < 1 || file.size > PRIVATE_DOCUMENT_MAX_BYTES)) setError(t.sizeError);
      return;
    }
    setBusy(true);setError('');
    const form = new FormData();
    form.set('file',file);
    form.set('category',category);
    form.set('privacy_ack','true');
    form.set('consent_version',PRIVATE_DOCUMENT_CONSENT_VERSION);
    try {
      const r = await fetch('/api/cases/' + caseId + '/private-documents',{
        method:'POST',credentials:'same-origin',body:form,
      });
      if (!r.ok) throw new Error('Upload failed');
      setFile(null);setAgreed(false);
      const input = document.getElementById('private-document-file') as HTMLInputElement|null;
      if (input) input.value = '';
      await load();
    } catch {setError(t.failed);}
    finally {setBusy(false);}
  }

  async function erase(id:string) {
    if (busy || !window.confirm(t.confirmDelete)) return;
    setBusy(true);setError('');
    try {
      const r = await fetch('/api/cases/' + caseId + '/private-documents/' + id,{
        method:'DELETE',credentials:'same-origin',
      });
      if (r.status !== 204) throw new Error('Delete failed');
      await load();
    } catch {setError(t.failed);}
    finally {setBusy(false);}
  }

  return <main className="subpage-background" id="main-content">
    <div className="container account-shell" style={{maxWidth: 760}}>
      <p><Link className="inline-link" href={'/cases/'+encodeURIComponent(caseId)}>{t.back}</Link></p>
      <h1 className="subpage-title">{t.title}</h1>
      <p>{t.lead}</p>
      {!signedIn || !configured ? <p>{configured ? t.signIn : t.unavailable}</p> : <>
        <section style={{marginTop:24}}>
          <label htmlFor="private-document-category">{t.category}</label>
          <select className="input" id="private-document-category"
            value={category} onChange={e=>setCategory(e.target.value)}>
            <option value="housing_document">{t.housing_document}</option>
            <option value="identity_document">{t.identity_document}</option>
            <option value="other_supporting_document">{t.other_supporting_document}</option>
          </select>
          <label htmlFor="private-document-file" style={{display:'block',marginTop:14}}>{t.choose}</label>
          <input id="private-document-file" type="file" accept="application/pdf,image/png,image/jpeg"
            onChange={e=>setFile(e.target.files?.[0]??null)} />
          <p style={{marginTop:16}}><Link href="/privacy/documents" className="inline-link" target="_blank">{t.privacy}</Link></p>
          <label style={{display:'flex',alignItems:'flex-start',gap:8,marginTop:12}}>
            <input type="checkbox" checked={agreed} onChange={e=>setAgreed(e.target.checked)} />
            <span>{t.consent}</span>
          </label>
          <button className="button button-primary" type="button" onClick={()=>void upload()}
            disabled={busy||!file||!agreed||file.size>PRIVATE_DOCUMENT_MAX_BYTES} style={{marginTop:16}}>
            {busy?t.uploading:t.upload}
          </button>
        </section>
        <section style={{marginTop:28}}>
          <h2>{t.stored}</h2>
          <button type="button" className="button button-outline" disabled={busy} onClick={()=>void load()}>{t.refresh}</button>
          {!loading && docs.length===0 && <p>{t.empty}</p>}
          <ul style={{paddingLeft:20}}>
            {docs.map(doc=><li key={doc.id} style={{marginTop:13}}>
              <strong>{t[doc.category as keyof typeof t]||doc.category}</strong>
              <p>{t.expires}: {new Date(doc.expires_at).toLocaleDateString(locale==='it'?'it-IT':'en-GB')}</p>
              <button type="button" disabled={busy} className="button button-outline"
                onClick={()=>void erase(doc.id)}>{t.delete}</button>
            </li>)}
          </ul>
          <p style={{fontSize:13,marginTop:18}}>{t.note}</p>
        </section>
      </>}
      {error && <p role="alert" className="error-text">{error}</p>}
    </div>
  </main>;
}
