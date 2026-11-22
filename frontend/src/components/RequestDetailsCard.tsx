'use client';

import {useCallback,useEffect,useState} from 'react';
import {requestIntakeState,INTAKE_FIELDS,INTAKE_OPTIONS,isRealCalendarDate}
  from '@/lib/request-intake.js';

type FieldKey =
  'citizenship_class'|'registration_context'|'destination_municipality'|
  'household_scope'|'housing_basis';
type Facts = Partial<Record<FieldKey,string>> & {move_in_date?:string};
type ApiIntake = {facts:Facts;confirmed:boolean;confirmed_at:string|null;
  missing_fields:string[];outside_first_scenario:string[];
  first_scenario_match:boolean;eligibility_evaluated:false;updated_at:string|null};

const labels = {
  en: {
    eyebrow:'DETAILS TO REVIEW',
    heading:'Review the information for this request',
    intro:'Review these details before we can determine which reviewed workflow applies. You can correct them here.',
    privacy:'Keep personal addresses, names, ID numbers and documents out of this form.',
    fields:{
      citizenship_class:'Citizenship category for this example',
      registration_context:'Previous registered residence in Italy',
      destination_municipality:'Destination municipality',
      household_scope:'Applicant household arrangement',
      housing_basis:'Housing arrangement',
    },
    options:{
      citizenship_class:{italian:'Italian',non_italian:'Non-Italian',unknown:'Not sure'},
      registration_context:{already_registered_in_italy:'Previously registered in Italy',arrival_from_abroad:'Arriving from abroad',unknown:'Not sure'},
      destination_municipality:{milano:'Milan',other:'Another municipality',unknown:'Not sure'},
      household_scope:{individual_no_aggregation:'Alone, not joining another household',joining_household:'Joining another household',multi_person:'Several applicants',unknown:'Not sure'},
      housing_basis:{registered_private_rental:'Registered private rental agreement',owner:'Owner',guest:'Guest',other:'Other arrangement',unknown:'Not sure'},
    },
    placeholder:'Choose an answer',
    date:'Move-in date (optional)',
    acknowledge:'I have reviewed the information above.',
    save:'Save draft',
    confirm:'Confirm facts',
    saving:'Saving…',
    reset:'Erase saved intake',
    resetConfirm:'Erase all saved details for this request?',
    saved:'Your information was saved. You can return to this conversation later.',
    confirmed:'Information confirmed for this request.',
    outside:'These answers do not match the narrow supported example. This is not an eligibility decision. Check the official instructions.',
    incomplete:'Some categorical questions remain unanswered or uncertain. Save a draft and return later.',
    status:'Intake status',
    updated:'Last saved',
    error:'Could not save or load these details. Try again.',
    retry:'Reload intake',
    confirmedState:'User confirmed',
    draftState:'Draft',
    archived:'This request is archived. Restore it before editing or confirming its details.',
    noLaw:'No legal eligibility, document requirements or government records have been checked.',
  },
  it: {
    eyebrow:'DATI DA CONTROLLARE',
    heading:'Controlla i dati di questa richiesta',
    intro:'Controlla questi dati per individuare il percorso revisionato applicabile. Puoi correggerli qui.',
    privacy:'Non inserire indirizzi, nomi, numeri identificativi o documenti personali.',
    fields:{
      citizenship_class:'Categoria di cittadinanza dell’esempio',
      registration_context:'Precedente residenza registrata in Italia',
      destination_municipality:'Comune di destinazione',
      household_scope:'Composizione della domanda',
      housing_basis:'Titolo di occupazione dell’abitazione',
    },
    options:{
      citizenship_class:{italian:'Italiana',non_italian:'Non italiana',unknown:'Non so'},
      registration_context:{already_registered_in_italy:'Già residente registrato in Italia',arrival_from_abroad:'Arrivo dall’estero',unknown:'Non so'},
      destination_municipality:{milano:'Milano',other:'Altro comune',unknown:'Non so'},
      household_scope:{individual_no_aggregation:'Da solo, senza ingresso in altro nucleo',joining_household:'Ingresso in nucleo esistente',multi_person:'Più richiedenti',unknown:'Non so'},
      housing_basis:{registered_private_rental:'Contratto di locazione privato registrato',owner:'Proprietario',guest:'Ospite',other:'Altro titolo',unknown:'Non so'},
    },
    placeholder:'Scegli una risposta',
    date:'Data del trasferimento (facoltativa)',
    acknowledge:'Ho controllato le informazioni qui sopra.',
    save:'Salva bozza',
    confirm:'Conferma i dati',
    saving:'Salvataggio…',
    reset:'Cancella dati salvati',
    resetConfirm:'Eliminare tutti i dati salvati per questa richiesta?',
    saved:'Dati salvati. Puoi riprendere questa conversazione più tardi.',
    confirmed:'Dati confermati per questa richiesta.',
    outside:'Queste risposte sono fuori dall’unico scenario supportato. Non è una decisione sull’ammissibilità. Consulta le fonti ufficiali.',
    incomplete:'Alcune risposte mancano o sono incerte. Salva una bozza e riprendi più tardi.',
    status:'Stato dei dati',
    updated:'Ultimo salvataggio',
    error:'Impossibile caricare o salvare i dati. Riprova.',
    retry:'Ricarica',
    confirmedState:'Confermato dall’utente',
    draftState:'Bozza',
    archived:'La richiesta è archiviata. Ripristinala prima di modificare o confermare i dati.',
    noLaw:'Non sono stati verificati requisiti legali, documenti necessari o registri ufficiali.',
  },
} as const;

export function RequestDetailsCard({taskId,language,onChanged,readOnly=false}:{taskId:string;language:'en'|'it';onChanged?:()=>void;readOnly?:boolean}) {
  const t=labels[language];
  const [facts,setFacts]=useState<Facts>({});
  const [stored,setStored]=useState<ApiIntake|null>(null);
  const [date,setDate]=useState('');
  const [ack,setAck]=useState(false);
  const [busy,setBusy]=useState(false);
  const [loading,setLoading]=useState(true);
  const [message,setMessage]=useState('');
  const [error,setError]=useState('');
  const [failure,setFailure]=useState<'load'|'draft'|'confirm'|null>(null);
  const [expired,setExpired]=useState(false);
  const load=useCallback(async(signal?:AbortSignal)=>{
    setLoading(true);setError('');setFailure(null);
    try{
      const r=await fetch('/api/conversations/tasks/'+taskId+'/intake',{
        credentials:'same-origin',cache:'no-store',signal,
      });
      if(r.status===401){if(!signal?.aborted)setExpired(true);return;}
      if(!r.ok) throw new Error('Request unavailable');
      const body=await r.json() as ApiIntake;
      if(!body||!body.facts||typeof body.facts!=='object') throw new Error('Bad intake');
      if(signal?.aborted) return;
      setExpired(false);setStored(body);
      setFacts(Object.fromEntries(INTAKE_FIELDS
        .filter(k=>typeof body.facts[k as FieldKey]==='string')
        .map(k=>[k,body.facts[k as FieldKey]])) as Facts);
      setDate(body.facts.move_in_date??'');
      setAck(false);
    }catch{if(!signal?.aborted){setFailure('load');}}
    finally{if(!signal?.aborted) setLoading(false);}
  },[taskId]);
  useEffect(()=>{
    const controller=new AbortController();
    void load(controller.signal);
    return ()=>controller.abort();
  },[load]);
  const state=requestIntakeState(facts,Boolean(stored?.confirmed));
  const localComplete=INTAKE_FIELDS.every(k=>typeof facts[k as FieldKey]==='string'&&
    facts[k as FieldKey]!=='unknown');
  const validDate=!date||isRealCalendarDate(date);
  async function persist(confirm:boolean){
    if(busy||expired||readOnly||!validDate||(confirm&&(!ack||!localComplete))) return;
    setBusy(true);setError('');setMessage('');setFailure(null);
    try{
      const payload={facts:{...facts,...(date?{move_in_date:date}:{})},confirm};
      const r=await fetch('/api/conversations/tasks/'+taskId+'/intake',{
        method:'PUT',headers:{'Content-Type':'application/json'},
        credentials:'same-origin',body:JSON.stringify(payload),
      });
      if(r.status===401){setExpired(true);return;}
      if(!r.ok) throw new Error('Save failed');
      const body=await r.json() as ApiIntake;
      setStored(body);
      setAck(false);
      onChanged?.();
      setMessage(confirm?t.confirmed:t.saved);
    }catch{setError(t.error);setFailure(confirm?'confirm':'draft');}
    finally{setBusy(false);}
  }
  async function erase(){
    if(busy||expired||readOnly||!window.confirm(t.resetConfirm))return;
    setBusy(true);setError('');setMessage('');setFailure(null);
    try{
      const r=await fetch('/api/conversations/tasks/'+taskId+'/intake',{method:'DELETE',credentials:'same-origin'});
      if(r.status===401){setExpired(true);return;}
      if(r.status!==204)throw new Error('Delete failed');
      setFacts({});setDate('');setAck(false);setStored(null);onChanged?.();setMessage(t.saved);
    }catch{setError(t.error);}
    finally{setBusy(false);}
  }
  function change(key:FieldKey,value:string){
    setFacts(old=>({...old,[key]:value}));
    setAck(false);
    // A change in the local form invalidates the previously displayed confirmation.
    setStored(old=>old?{...old,confirmed:false}:old);
    setMessage('');
  }
  return <section id="request-details" aria-label={t.heading} className="intake-sheet">
    <span className="tiny-eyebrow">{t.eyebrow}</span>
    <h3 style={{marginTop:10}}>{t.heading}</h3>
    <p>{t.intro}</p>
    <div className="message-box notice" style={{marginTop:12}}><div><p>{t.privacy}</p></div></div>
    {readOnly&&<p role="status">{t.archived}</p>}
    {loading?<p className="editorial-pending" role="status">{language === 'it' ? 'Caricamento…' : 'Loading…'}</p>:<>
      <div style={{display:'grid',gap:16,marginTop:20}}>
        {INTAKE_FIELDS.map(key=>{
          const field=key as FieldKey;
          const optionLabels: Record<string,string> = t.options[field];
          return <div key={field}>
            <label htmlFor={'intake-'+field} className="field-label">{t.fields[field]}</label>
            <select id={'intake-'+field} className="input" value={facts[field]??''}
              disabled={busy||expired||readOnly}
              onChange={e=>change(field,e.target.value)}>
              <option value="">{t.placeholder}</option>
              {INTAKE_OPTIONS[field].map(value=><option key={value} value={value}>
                {optionLabels[value]??value}
              </option>)}
            </select>
          </div>;
        })}
        <div>
          <label htmlFor="intake-move-date" className="field-label">{t.date}</label>
          <input className="input" id="intake-move-date" type="date" value={date}
            min="1900-01-01" max="2100-12-31" disabled={busy||expired||readOnly}
            onChange={e=>{setDate(e.target.value);setStored(old=>old?{...old,confirmed:false}:old);setAck(false);setMessage('');}}/>
        </div>
      </div>
      <div style={{marginTop:18}}>
        <p><strong>{t.status}:</strong> {stored?.confirmed?t.confirmedState:t.draftState}</p>
        {stored?.updated_at&&<p style={{fontSize:12,opacity:0.8}}>{t.updated}: {new Date(stored.updated_at).toLocaleString(language==='it'?'it-IT':'en-GB')}</p>}
        {state==='outside_first_scenario'&&<p role="status">{t.outside}</p>}
        {state==='incomplete'&&<p role="status">{t.incomplete}</p>}
        <label style={{display:'flex',alignItems:'flex-start',gap:8}}>
          <input type="checkbox" checked={ack} disabled={busy||expired||readOnly}
            onChange={e=>setAck(e.target.checked)}/>
          <span>{t.acknowledge}</span>
        </label>
        <div style={{display:'flex',flexWrap:'wrap',gap:8,marginTop:12}}>
          <button type="button" className="button button-outline" disabled={busy||expired||readOnly||!validDate}
            onClick={()=>void persist(false)}>{busy?t.saving:t.save}</button>
          <button type="button" className="button button-primary" disabled={busy||expired||readOnly||!ack||!localComplete||!validDate}
            onClick={()=>void persist(true)}>{busy?t.saving:t.confirm}</button>
          <button type="button" className="button button-outline" disabled={busy||expired||readOnly}
            onClick={()=>void erase()}>{t.reset}</button>
        </div>
      </div>
    </>}
    {message&&<p role="status">{message}</p>}
    {error&&<p role="alert" className="error-text">{error}
      <button type="button" className="button button-outline" onClick={()=>void load()}>{t.retry}</button>
    </p>}
    <p style={{fontSize:12,opacity:0.8,marginTop:14}}>{t.noLaw}</p>
  </section>;
}
