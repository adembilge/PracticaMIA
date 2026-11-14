'use client';

import {useCallback,useEffect,useMemo,useState} from 'react';
import Link from 'next/link';
import {Icon} from '@/components/Icon';
import {useDemo} from '@/components/DemoProvider';
import {
  INTAKE_HOUSING_VALUES,validIntelligenceResponse,
  reviewFormDefaults,canEditDocumentReview,
} from '@/lib/private-document-intelligence.js';

type Candidate={
  candidate_id:string;field_name:'housing_basis'|'move_in_date';
  raw_value:string;suggested_value:string;page:number;
};
type Comparison={field_name:string;reviewed_value:string;
  case_value:string|null;comparison:'match'|'conflict'|'no_confirmed_case_fact'};
type Review={
  status:string;candidates:Candidate[];comparisons:Comparison[];
  ambiguous_fields:string[];extraction_digest:string|null;
  confirmed_fields:Record<string,string>;user_reviewed:boolean;
  selected_evidence?:Record<string,string>;
  no_legal_verification:true;official_submission:false;
};
type Props={caseId:string;documentId:string};
const words={
  en:{
    title:'Local document field review',
    privacy:'Only two supported fields are extracted locally. No full page text or document content goes to an AI model. Results are not legal validation.',
    extract:'Extract fields',
    extracting:'Extracting…',
    missing:'No supported labeled housing or move-in date fields were found. Review the document yourself.',
    unreadable:'No readable text was found. Try a clearer scan or a PDF with selectable text.',
    needExtract:'Extract fields to see source-backed suggestions.',
    unsupported:'This document category is not supported for automated field extraction.',
    reviewing:'Review suggested fields and correct them if necessary. Never accept text without checking the document.',
    field_housing_basis:'Housing arrangement',
    field_move_in_date:'Move-in date',
    page:'Page',
    suggested:'Suggested from the document',
    actual:'Reviewed value',
    choose:'Choose supporting suggestion',
    disclaimer:'I checked each selected field against this document. These are my corrections and do not change the saved case intake.',
    save:'Save my review',
    update:'Update my review',
    saving:'Saving…',
    match:'Matches confirmed case fact',
    conflict:'Disagrees with confirmed case fact — update your case intake or clarify the document',
    absent:'No confirmed corresponding case fact',
    ambiguous:'Conflicting labels in this file require manual review. The app will not resolve the disagreement automatically.',
    reviewed:'User-reviewed values saved in encrypted temporary storage. No official verification occurred.',
    needsIntake:'Confirm your case intake to compare the document values.',
    needsCaseInfo:'A reviewed field is missing from your confirmed case. Update case intake before downloading a PDF draft.',
    reload:'Reload review',
    error:'Document review could not be completed. Check the saved file and try again.',
    options:{
      registered_private_rental:'Registered private rental',
      owner:'Owner',guest:'Guest',other:'Other',
    },
  },
  it:{
    title:'Revisione locale dei dati estratti',
    privacy:'Vengono estratti localmente solo due campi. Il contenuto del documento non viene inviato a un modello AI. I risultati non costituiscono una verifica legale.',
    extract:'Estrai i campi',
    extracting:'Estrazione…',
    missing:'Non sono stati trovati campi riconosciuti relativi all’alloggio o alla data. Verifica il documento manualmente.',
    unreadable:'Non è stato trovato testo leggibile. Prova una scansione più nitida o un PDF con testo selezionabile.',
    needExtract:'Estrai i campi per vedere i suggerimenti collegati al documento.',
    unsupported:'Questa categoria di documenti non supporta l’estrazione automatica.',
    reviewing:'Controlla e correggi i valori suggeriti. Confrontali sempre con il documento.',
    field_housing_basis:'Titolo di occupazione',
    field_move_in_date:'Data del trasferimento',
    page:'Pagina',
    suggested:'Suggerimento dal documento',
    actual:'Valore verificato dall’utente',
    choose:'Scegli il suggerimento corrispondente',
    disclaimer:'Ho verificato tutti i campi rispetto al documento. Le correzioni non modificano i dati della pratica.',
    save:'Salva la mia revisione',
    update:'Aggiorna la mia revisione',
    saving:'Salvataggio…',
    match:'Corrisponde al dato confermato nella pratica',
    conflict:'In disaccordo con la pratica — correggi i dati o chiarisci il documento',
    absent:'Dato corrispondente non confermato nella pratica',
    ambiguous:'Il file contiene valori contrastanti. Serve una revisione manuale; l’app non sceglie automaticamente.',
    reviewed:'Valori confermati dall’utente e salvati in archivio cifrato. Nessuna verifica ufficiale.',
    needsIntake:'Conferma la raccolta dati della pratica per eseguire il confronto.',
    needsCaseInfo:'Un campo revisionato non è presente nei dati confermati della pratica. Aggiorna i dati prima di scaricare il PDF.',
    reload:'Ricarica la revisione',
    error:'Impossibile completare la revisione. Verifica il file e riprova.',
    options:{
      registered_private_rental:'Locazione privata registrata',
      owner:'Proprietario',guest:'Ospite',other:'Altro',
    },
  },
} as const;

export function PrivateDocumentIntelligence({caseId,documentId}:Props) {
  const {locale}=useDemo();
  const t=words[locale];
  const [review,setReview]=useState<Review|null>(null);
  const [chosen,setChosen]=useState<Record<string,string>>({});
  const [corrected,setCorrected]=useState<Record<string,string>>({});
  const [approved,setApproved]=useState(false);
  const [operation,setOperation]=useState<'extract'|'review'|null>(null);
  const [expired,setExpired]=useState(false);
  const [loading,setLoading]=useState(true);
  const [failure,setFailure]=useState<'load'|'extract'|'review'|null>(null);
  const busy=operation!==null||loading;
  const [error,setError]=useState('');
  const base='/api/cases/'+caseId+'/private-documents/'+documentId+'/intelligence';

  const adopt=(data:Review)=>{
    setReview(data);
    const defaults=reviewFormDefaults(data);
    setChosen(defaults.selected as Record<string,string>);
    setCorrected(defaults.corrected as Record<string,string>);
    setApproved(false);
  };

  const load=useCallback(async(signal?:AbortSignal)=>{
    setError('');setFailure(null);setLoading(true);
    try{
      const response=await fetch(base,{cache:'no-store',credentials:'same-origin',signal});
      if(response.status===401){if(!signal?.aborted)setExpired(true);return;}
      if(!response.ok)throw new Error('Unable to load');
      const raw:unknown=await response.json();
      if(!validIntelligenceResponse(raw))throw new Error('Bad response');
      if(!signal?.aborted){adopt(raw as Review);setExpired(false);}
    }catch{if(!signal?.aborted){setError(words[locale].error);setFailure('load');}}
    finally{if(!signal?.aborted)setLoading(false);}
  },[base,locale]);

  useEffect(()=>{
    const controller=new AbortController();
    void load(controller.signal);
    return ()=>controller.abort();
  },[load]);

  const groups=useMemo(()=>{
    const map:Record<string,Candidate[]>={};
    for(const item of review?.candidates??[]){
      (map[item.field_name]??=[]).push(item);
    }
    return Object.entries(map);
  },[review]);

  async function extract(){
    if(busy||expired)return;
    setOperation('extract');setError('');setFailure(null);
    try{
      const response=await fetch(base+'/extract',{method:'POST',credentials:'same-origin'});
      if(response.status===401){setExpired(true);return;}
      if(!response.ok)throw new Error('Extraction rejected');
      const raw:unknown=await response.json();
      if(!validIntelligenceResponse(raw))throw new Error('Bad response');
      adopt(raw as Review);
    }catch{setError(t.error);setFailure('extract');}
    finally{setOperation(null);}
  }

  async function confirm(){
    if(busy||expired||!approved||!review?.extraction_digest)return;
    setOperation('review');setError('');setFailure(null);
    try{
      const selections=groups.map(([field_name,items])=>({
        field_name,
        candidate_id:chosen[field_name]??items[0].candidate_id,
        confirmed_value:corrected[field_name]??items[0].suggested_value,
      }));
      const response=await fetch(base+'/review',{
        method:'PUT',credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          extraction_digest:review.extraction_digest,
          selections,confirm:true,
        }),
      });
      if(response.status===401){setExpired(true);return;}
      if(!response.ok)throw new Error('Review rejected');
      const raw:unknown=await response.json();
      if(!validIntelligenceResponse(raw))throw new Error('Bad response');
      adopt(raw as Review);
    }catch{setError(t.error);setFailure('review');}
    finally{setOperation(null);}
  }

  const status=review?.status;
  const isUnprocessed=status==='needs_extraction';
  const canReview=canEditDocumentReview(review)&&groups.length>0;

  const it=locale==='it';
  const fieldLabel=(field:string)=>field==='housing_basis'?t.field_housing_basis:t.field_move_in_date;
  const displayValue=(value:string|null)=>value===null?'—':t.options[value as keyof typeof t.options]??value;
  const intakeLink='/cases/'+encodeURIComponent(caseId)+'#case-intake';

  return <section aria-label={t.title} className="document-review" aria-busy={busy}>
    <h3>{t.title}</h3><p className="document-lead">{t.privacy}</p>
    {loading&&<p className="editorial-pending" role="status">{it?'Caricamento revisione…':'Loading document review…'}</p>}
    {operation&&<p className="editorial-pending" role="status">{operation==='extract'?t.extracting:t.saving}</p>}
    {expired&&<div className="message-box warning" role="alert"><div>
      <p>{it?'La sessione è scaduta.':'Your session has expired.'}</p>
      <a className="inline-link" href={'/auth/login?returnTo='+encodeURIComponent('/cases/'+caseId+'/documents')}>{it?'Accedi di nuovo':'Sign in again'}</a>
    </div></div>}
    {status==='unsupported_category'&&<p className="case-state" role="status">{t.unsupported}</p>}
    {isUnprocessed&&<div className="case-state">
      <Icon name="file"/><div><p>{t.needExtract}</p>
        <button type="button" className="button button-primary" onClick={()=>void extract()} disabled={busy||expired}>{t.extract}</button>
      </div>
    </div>}
    {status==='no_supported_fields'&&<p className="case-state" role="status">{t.missing}</p>}
    {status==='unreadable'&&<p className="case-state" role="alert">{t.unreadable}</p>}
    {status==='needs_manual_review'&&<p className="case-state" role="alert">{t.ambiguous}</p>}
    {(status==='needs_confirmed_intake'||status==='needs_case_information')&&<div className="case-state" role="status"><div>
      <p>{status==='needs_confirmed_intake'?t.needsIntake:t.needsCaseInfo}</p>
      <Link className="inline-link" href={intakeLink}>{it?'Apri i dati della pratica':'Open case details'} →</Link>
    </div></div>}
    {review?.user_reviewed&&<p className="case-confirmation" role="status"><Icon name="check" size={16}/>{t.reviewed}</p>}
    {canReview&&<>
      <p>{t.reviewing}</p>
      {review?.ambiguous_fields.length ? <p className="case-state" role="alert">{t.ambiguous}</p> : null}
      <div className="document-comparison">
        <aside className="document-evidence">
          <p className="editorial-label">{it?'Riferimenti nel documento':'Document evidence'}</p>
          {groups.map(([field,items])=>{
            const evidence=items.find(item=>item.candidate_id===chosen[field])??items[0];
            return <div key={field}><small>{t.page} {evidence.page}</small>
              <strong>{fieldLabel(field)}</strong><p>{evidence.raw_value}</p></div>;
          })}
        </aside>
        <div>
          {groups.map(([field,items])=>{
            const controlId='doc-confirm-'+documentId+'-'+field;
            const comparison=review?.comparisons.find(entry=>entry.field_name===field);
            return <fieldset key={field} className="document-field" disabled={busy||expired}>
              <legend>{fieldLabel(field)}</legend>
              <label className="field-label" htmlFor={'doc-evidence-'+documentId+'-'+field}>{t.choose}</label>
              <select className="input" id={'doc-evidence-'+documentId+'-'+field} value={chosen[field]??''}
                onChange={e=>{
                  const item=items.find(candidate=>candidate.candidate_id===e.target.value);
                  if(!item)return;
                  setChosen(old=>({...old,[field]:item.candidate_id}));
                  setCorrected(old=>({...old,[field]:item.suggested_value}));
                  setApproved(false);
                }}>
                {items.map(item=><option key={item.candidate_id} value={item.candidate_id}>{t.page} {item.page} · {item.raw_value}</option>)}
              </select>
              <label className="field-label" htmlFor={controlId}>{t.actual}</label>
              {field==='housing_basis' ? <select className="input" id={controlId} value={corrected[field]??''}
                onChange={e=>{setCorrected(old=>({...old,[field]:e.target.value}));setApproved(false);}}>
                {INTAKE_HOUSING_VALUES.map(value=><option key={value} value={value}>{t.options[value as keyof typeof t.options]}</option>)}
              </select> : <input type="date" className="input" id={controlId} value={corrected[field]??''}
                min="1900-01-01" max="2100-12-31"
                onChange={e=>{setCorrected(old=>({...old,[field]:e.target.value}));setApproved(false);}}/>}
              {comparison&&<div className={'document-result '+(comparison.comparison==='match'?'document-match':'document-conflict')}>
                <strong>{comparison.comparison==='match'?t.match:comparison.comparison==='conflict'?t.conflict:t.absent}</strong>
                <p>{it?'Nei dati confermati':'Confirmed case value'} <b>{displayValue(comparison.case_value)}</b></p>
                {comparison.comparison==='conflict'&&<button className="inline-link" type="button"
                  onClick={()=>document.getElementById(controlId)?.focus()}>{it?'Esamina il campo':'Review field'} →</button>}
              </div>}
            </fieldset>;
          })}
        </div>
      </div>
      <label className="document-consent">
        <input type="checkbox" checked={approved} disabled={busy||expired} onChange={e=>setApproved(e.target.checked)}/>
        <span>{t.disclaimer}</span>
      </label>
      <button type="button" className="button button-primary" disabled={!approved||busy||expired}
        onClick={()=>void confirm()}>{review?.user_reviewed?t.update:t.save}</button>
    </>}
    <button type="button" className="inline-link workflow-refresh" disabled={busy||expired} onClick={()=>void load()}>{t.reload}</button>
    {error&&<div className="message-box warning" role="alert"><div><p>{error}</p>
      <button type="button" className="inline-link" disabled={busy||expired} onClick={()=>{
        if(failure==='extract')void extract();
        else if(failure==='review')void confirm();
        else void load();
      }}>{it?'Riprova':'Try again'}</button>
    </div></div>}
  </section>;
}
