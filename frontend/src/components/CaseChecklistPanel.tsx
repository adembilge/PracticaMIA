'use client';

import {useEffect,useState} from 'react';
import {useDemo} from '@/components/DemoProvider';
import {FIRST_ROUTE_SOURCE_LINKS} from '@/lib/approved-source-view.js';

type Evidence = {
  citation_id:string; source_id:string; source_version_id:string;
  title:string; institution:string; official_url:string;
  reviewed_at:string; retrieved_at:string; archived_reference:boolean;
};
type Item = {
  id:string; description:string; status:'needs_user';
  obligation_class:'reviewed_action'; evidence:Evidence[];
};
type Checklist = {
  status:string;next_action:string;items:Item[];
  ruleset_version:string|null;verified_evidence:boolean;
  synthetic_only:boolean;eligibility_evaluated:boolean;
  government_submitted:boolean;required_document_types:string[];
  missing_fields:string[];
};
const sourceVersions:Record<string,string> = {
  'milano-italian-residence-change':'e139e910-3a89-4994-b450-b5107d8db7dd',
  'anpr-public-docs-residence-guide':'c89b4c40-4c41-48d5-ad52-be08e9630277',
};
const labels = {
  en:{
    title:'Case-specific reviewed checklist',
    intro:'Calculated from confirmed example facts and the signed, source-reviewed first Milan rule catalog. Not an official decision.',
    notConfirmed:'Confirm your saved intake above to request the reviewed checklist.',
    loading:'Checking the approved sources…',
    unavailable:'Reviewed checklist cannot be displayed. No unsupported requirements will be substituted.',
    retry:'Check again',
    needs_scope:'Complete the five product-scope questions before requesting a checklist.',
    needs_confirmation:'Save and confirm the five categorical intake answers.',
    outside_first_route:'These facts are outside the one supported example. This is not a legal rejection.',
    evidence_unavailable:'Some approved rule or source evidence is unavailable. Consult official services; no checklist has been issued.',
    ready:'Five source-backed actions for this supported example',
    original:'The following descriptions are the exact signed English rule text.',
    source:'Reviewed source',
    reviewed:'Internally reviewed',
    archived:'Archived ANPR edition — not confirmed current',
    noDocs:'The reviewed catalog contains no mandatory document categories for this narrow scenario. This is not proof that the current ANPR service requires no attachments.',
    warning:'No eligibility or document verification was performed. No government submission occurred. Verify the current forms and instructions on the official websites.',
    version:'Signed ruleset',
  },
  it:{
    title:'Lista delle azioni revisionate per la pratica',
    intro:'Calcolata dai dati confermati dell’esempio e dalle regole firmate con fonti revisionate. Non è una decisione ufficiale.',
    notConfirmed:'Conferma prima i dati salvati per ottenere la lista revisionata.',
    loading:'Verifica delle fonti approvate…',
    unavailable:'Impossibile mostrare la lista revisionata. Non verranno suggeriti requisiti non verificati.',
    retry:'Verifica di nuovo',
    needs_scope:'Completa le cinque domande iniziali prima della lista.',
    needs_confirmation:'Salva e conferma le cinque risposte della raccolta dati.',
    outside_first_route:'I dati non corrispondono all’unico esempio supportato. Non è un rifiuto legale.',
    evidence_unavailable:'Una regola o fonte revisionata non è disponibile. Consulta i servizi ufficiali; nessuna lista è stata emessa.',
    ready:'Cinque azioni con fonti revisionate per questo esempio',
    original:'Le descrizioni sono riportate in inglese esattamente come nel catalogo firmato.',
    source:'Fonte revisionata',
    reviewed:'Revisionata internamente',
    archived:'Edizione ANPR archiviata — attualità non confermata',
    noDocs:'Il catalogo revisionato non definisce categorie di documenti obbligatori per questo scenario limitato. Non significa che l’ANPR attuale non chieda allegati.',
    warning:'Nessuna verifica di idoneità o documentale è stata effettuata. Nessuna domanda è stata inviata. Verifica i moduli e le istruzioni attuali sui siti ufficiali.',
    version:'Versione delle regole firmate',
  },
} as const;

function verifiedEvidence(e:Evidence):boolean {
  const expected=FIRST_ROUTE_SOURCE_LINKS[e.source_id as keyof typeof FIRST_ROUTE_SOURCE_LINKS];
  return Boolean(expected && expected.url===e.official_url &&
    e.source_version_id===sourceVersions[e.source_id] &&
    e.citation_id.startsWith(e.source_version_id+':') &&
    e.archived_reference===(e.source_id==='anpr-public-docs-residence-guide'));
}

function validChecklist(v:unknown):v is Checklist {
  if(!v||typeof v!=='object'||Array.isArray(v))return false;
  const x=v as Partial<Checklist>;
  if(typeof x.status!=='string'||!Array.isArray(x.items)||typeof x.next_action!=='string'||
    x.synthetic_only!==true||x.eligibility_evaluated!==false||x.government_submitted!==false)return false;
  if(x.status==='ready_for_user_review'){
    return x.verified_evidence===true&&x.items.length===5&&
      Array.isArray(x.required_document_types)&&x.required_document_types.length===0&&
      x.items.every(i=>i&&typeof i.id==='string'&&typeof i.description==='string'&&
        i.status==='needs_user'&&Array.isArray(i.evidence)&&i.evidence.length>0&&
        i.evidence.every(verifiedEvidence));
  }
  return x.items.length===0;
}

export function CaseChecklistPanel({caseId,revision,confirmed}:{
  caseId:string;revision:number;confirmed:boolean;
}) {
  const {locale}=useDemo();
  const t=labels[locale];
  const [data,setData]=useState<Checklist|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const [attempt,setAttempt]=useState(0);

  useEffect(()=>{
    if(!confirmed){setData(null);setLoading(false);setError('');return;}
    const controller=new AbortController();
    setLoading(true);setData(null);setError('');
    fetch('/api/cases/'+caseId+'/checklist',{
      credentials:'same-origin',cache:'no-store',signal:controller.signal,
    }).then(async r=>{
      if(!r.ok)throw new Error('Checklist unavailable');
      const payload:unknown=await r.json();
      if(!validChecklist(payload))throw new Error('Invalid checklist');
      return payload;
    }).then(payload=>{if(!controller.signal.aborted)setData(payload);})
      .catch(()=>{if(!controller.signal.aborted)setError(t.unavailable);})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[caseId,revision,confirmed,attempt,t.unavailable]);

  return <section aria-label={t.title} style={{
    marginTop:24,padding:18,border:'1px solid #d6e5e8',borderRadius:12,
  }}>
    <h3 style={{marginTop:0}}>{t.title}</h3>
    <p>{t.intro}</p>
    {!confirmed?<p role="status">{t.notConfirmed}</p>:<>
      {loading&&<p role="status">{t.loading}</p>}
      {error&&<p role="alert">{error}</p>}
      {data&&data.status!=='ready_for_user_review'&&
        <p role="status">{t[data.status as keyof typeof t]||t.unavailable}</p>}
      {data?.status==='ready_for_user_review'&&<>
        <h4>{t.ready}</h4>
        <p style={{fontSize:13}}>{t.original}</p>
        <p style={{fontSize:12,opacity:0.85}}><strong>{t.version}:</strong> {data.ruleset_version}</p>
        <ol style={{paddingLeft:22}}>
          {data.items.map(item=><li key={item.id} style={{marginBottom:18}}>
            <p style={{marginBottom:6}}><strong>{item.description}</strong></p>
            <ul style={{paddingLeft:18,fontSize:13}}>
              {item.evidence.map(e=><li key={e.citation_id}>
                <a href={FIRST_ROUTE_SOURCE_LINKS[e.source_id as keyof typeof FIRST_ROUTE_SOURCE_LINKS].url}
                   className="inline-link" target="_blank" rel="noopener noreferrer">
                  {t.source}: {e.title}
                </a>
                {' · '}{t.reviewed}: {e.reviewed_at.slice(0,10)}
                {e.archived_reference&&<strong> · {t.archived}</strong>}
              </li>)}
            </ul>
          </li>)}
        </ol>
        <p>{t.noDocs}</p>
      </>}
      <button type="button" className="button button-outline" style={{marginTop:10}}
        disabled={loading} onClick={()=>setAttempt(n=>n+1)}>{t.retry}</button>
    </>}
    <p style={{fontSize:12,opacity:0.85,marginTop:14}}>{t.warning}</p>
  </section>;
}
