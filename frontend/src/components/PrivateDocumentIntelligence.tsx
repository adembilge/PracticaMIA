'use client';

import {useCallback,useEffect,useMemo,useState} from 'react';
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
    unreadable:'This document has no readable text. Local OCR may be needed for scanned images.',
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
    unreadable:'Non è stato trovato testo leggibile. Potrebbe servire OCR locale per le immagini.',
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
  const [busy,setBusy]=useState(false);
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
    setError('');
    try{
      const response=await fetch(base,{cache:'no-store',credentials:'same-origin',signal});
      if(!response.ok)throw new Error('Unable to load');
      const raw:unknown=await response.json();
      if(!validIntelligenceResponse(raw))throw new Error('Bad response');
      if(!signal?.aborted)adopt(raw as Review);
    }catch{if(!signal?.aborted)setError(words[locale].error);}
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
    if(busy)return;
    setBusy(true);setError('');
    try{
      const response=await fetch(base+'/extract',{method:'POST',credentials:'same-origin'});
      if(!response.ok)throw new Error('Extraction rejected');
      const raw:unknown=await response.json();
      if(!validIntelligenceResponse(raw))throw new Error('Bad response');
      adopt(raw as Review);
    }catch{setError(t.error);}
    finally{setBusy(false);}
  }

  async function confirm(){
    if(busy||!approved||!review?.extraction_digest)return;
    setBusy(true);setError('');
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
      if(!response.ok)throw new Error('Review rejected');
      const raw:unknown=await response.json();
      if(!validIntelligenceResponse(raw))throw new Error('Bad response');
      adopt(raw as Review);
    }catch{setError(t.error);}
    finally{setBusy(false);}
  }

  const status=review?.status;
  const isUnprocessed=status==='needs_extraction';
  const canReview=canEditDocumentReview(review)&&groups.length>0;

  return <section aria-label={t.title} style={{padding:14,marginTop:10,border:'1px solid #d6e5e8',borderRadius:10}}>
    <h4>{t.title}</h4>
    <p style={{fontSize:12}}>{t.privacy}</p>
    {!review&&!error&&<p role="status">{t.extracting}</p>}
    {status==='unsupported_category'&&<p role="status">{t.unsupported}</p>}
    {isUnprocessed&&<>
      <p>{t.needExtract}</p>
      <button type="button" className="button button-outline"
        onClick={()=>void extract()} disabled={busy}>
        {busy?t.extracting:t.extract}
      </button>
    </>}
    {status==='no_supported_fields'&&<p role="status">{t.missing}</p>}
    {status==='unreadable'&&<p role="status">{t.unreadable}</p>}
    {status==='needs_manual_review'&&<p role="status">{t.ambiguous}</p>}
    {status==='needs_confirmed_intake'&&<p role="status">{t.needsIntake}</p>}
    {canReview&&<>
      <p>{t.reviewing}</p>
      {review?.ambiguous_fields.length? <p role="alert">{t.ambiguous}</p>:null}
      {groups.map(([field,items])=><div key={field} style={{marginTop:12}}>
        <strong>{field==='housing_basis'?t.field_housing_basis:t.field_move_in_date}</strong>
        <label htmlFor={'doc-evidence-'+documentId+'-'+field} style={{display:'block',marginTop:5}}>{t.choose}</label>
        <select className="input" id={'doc-evidence-'+documentId+'-'+field}
          value={chosen[field]??''}
          onChange={e=>{
            const item=items.find(i=>i.candidate_id===e.target.value);
            if(!item)return;
            setChosen(old=>({...old,[field]:e.target.value}));
            setCorrected(old=>({...old,[field]:item.suggested_value}));
            setApproved(false);
          }}>
          {items.map(item=><option key={item.candidate_id} value={item.candidate_id}>
            {t.page} {item.page} · {t.suggested}: {item.raw_value}
          </option>)}
        </select>
        <label htmlFor={'doc-confirm-'+documentId+'-'+field} style={{display:'block',marginTop:5}}>{t.actual}</label>
        {field==='housing_basis'? <select className="input"
          id={'doc-confirm-'+documentId+'-'+field}
          value={corrected[field]??''}
          onChange={e=>{setCorrected(old=>({...old,[field]:e.target.value}));setApproved(false);}}>
          {INTAKE_HOUSING_VALUES.map(value=><option key={value} value={value}>
            {t.options[value as keyof typeof t.options]}
          </option>)}
        </select>:<input type="date" className="input"
          id={'doc-confirm-'+documentId+'-'+field}
          value={corrected[field]??''}
          min="1900-01-01" max="2100-12-31"
          onChange={e=>{setCorrected(old=>({...old,[field]:e.target.value}));setApproved(false);}}/>}
      </div>)}
      <label style={{display:'flex',gap:8,alignItems:'flex-start',marginTop:12}}>
        <input type="checkbox" checked={approved}
          onChange={e=>setApproved(e.target.checked)}/>
        <span>{t.disclaimer}</span>
      </label>
      <button type="button" className="button button-primary" style={{marginTop:10}}
        disabled={!approved||busy}
        onClick={()=>void confirm()}>{busy?t.saving:review?.user_reviewed?t.update:t.save}</button>
    </>}
    {review?.user_reviewed&&<>
      <p><strong>{t.reviewed}</strong></p>
      {review.comparisons.map(c=><p key={c.field_name}>
        <strong>{c.field_name==='housing_basis'?t.field_housing_basis:t.field_move_in_date}:</strong>
        {' '}{c.reviewed_value}
        {' — '}{c.comparison==='match'?t.match:c.comparison==='conflict'?t.conflict:t.absent}
      </p>)}
    </>}
    <button type="button" className="button button-outline"
      style={{marginTop:8}} disabled={busy}
      onClick={()=>void load()}>{t.reload}</button>
    {error&&<p role="alert">{error}</p>}
  </section>;
}
