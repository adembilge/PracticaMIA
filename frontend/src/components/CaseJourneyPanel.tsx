'use client';

import Link from 'next/link';
import {useCallback,useEffect,useState} from 'react';
import {useDemo} from '@/components/DemoProvider';
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
      locked:'Not ready',informational:'Optional explanation',
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
      locked:'Non disponibile',informational:'Spiegazione facoltativa',
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

const nextTarget:Record<string,string>={
  answer_scope:'#case-scope',
  confirm_intake:'#case-intake',
  consult_official:'#case-handoff',
  review_sources:'#case-sources',
  review_checklist:'#case-workflow-checklist',
  resolve_documents:'#case-workflow-documents',
  download_draft:'#case-workflow-package',
  review_package:'#case-workflow-package',
};
const target:Record<string,string>={
  scope:'#case-scope',intake:'#case-intake',guidance:'#case-ai',
  checklist:'#case-workflow-checklist',documents:'#case-workflow-documents',
  package:'#case-workflow-package',handoff:'#case-handoff',
};

export function CaseJourneyPanel({caseId,refreshKey,privateDocumentsEnabled,liveAIEnabled}:{
  caseId:string;refreshKey:number;privateDocumentsEnabled:boolean;liveAIEnabled:boolean;
}) {
  const {locale}=useDemo();
  const t=copy[locale];
  const [data,setData]=useState<Workflow|null>(null);
  const [loading,setLoading]=useState(false);
  const [saving,setSaving]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [revision,setRevision]=useState(0);

  const load=useCallback(async(signal?:AbortSignal)=>{
    setLoading(true);setError('');setNotice('');
    try{
      const response=await fetch('/api/cases/'+caseId+'/workflow',{
        credentials:'same-origin',cache:'no-store',signal,
      });
      if(!response.ok)throw new Error('Workflow unavailable');
      const payload:unknown=await response.json();
      if(!validCaseWorkflow(payload))throw new Error('Invalid workflow');
      if(!signal?.aborted)setData(payload as Workflow);
    }catch{
      if(!signal?.aborted){setData(null);setError(copy[locale].loadError);}
    }finally{if(!signal?.aborted)setLoading(false);}
  },[caseId,locale]);

  useEffect(()=>{
    const controller=new AbortController();
    void load(controller.signal);
    return ()=>controller.abort();
  },[load,refreshKey,revision]);

  async function mark(itemId:string,reviewed:boolean){
    if(!data?.checklist.fingerprint||saving)return;
    setSaving(true);setError('');setNotice('');
    try{
      const response=await fetch('/api/cases/'+caseId+'/workflow/checklist',{
        method:'PATCH',credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          item_id:itemId,reviewed,fingerprint:data.checklist.fingerprint,
        }),
      });
      if(!response.ok)throw new Error('Stale checklist');
      const payload:unknown=await response.json();
      if(!validCaseWorkflow(payload))throw new Error('Invalid workflow');
      setData(payload as Workflow);
      setNotice(t.updated);
    }catch{
      setError(t.error);
      setRevision(x=>x+1);
    }finally{setSaving(false);}
  }
  const reviewed=data?.checklist.reviewed_items??{};
  return <section id="case-workflow" aria-label={t.heading}
    style={{border:'1px solid #cbdce4',borderRadius:12,padding:18,margin:'15px 0'}}>
    <h2 style={{marginTop:0}}>{t.heading}</h2>
    <p>{t.intro}</p>
    {loading&&<p role="status">{t.loading}</p>}
    {error&&<p role="alert">{error}</p>}
    {data&&<>
      <nav aria-label={t.heading} style={{
        display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(155px,1fr))',
        gap:8,marginTop:18,
      }}>
        {data.steps.map((step,i)=>{
          const unavailable=(step.id==='documents'&&!privateDocumentsEnabled)||
            (step.id==='guidance'&&!liveAIEnabled);
          return <a key={step.id} href={target[step.id]}
            aria-disabled={unavailable}
            style={{
              padding:12,border:'1px solid #d8e2e7',borderRadius:8,
              textDecoration:'none',opacity:unavailable?0.55:1,
            }}>
            <span style={{display:'block',fontSize:12,opacity:0.75}}>
              {String(i+1).padStart(2,'0')} · {t.state[step.status as keyof typeof t.state]??step.status}
            </span>
            <strong>{t.stages[step.id as keyof typeof t.stages]??step.id}</strong>
          </a>;
        })}
      </nav>
      <div className="message-box notice" role="status" style={{marginTop:15}}>
        <div>
          <strong>{t.summary}</strong>
          <p>{t.action[data.next_action as keyof typeof t.action]??data.next_action}</p>
          <a href={nextTarget[data.next_action]??'#case-intake'} className="inline-link">
            {t.stages[(data.next_action==='answer_scope'?'scope':
              data.next_action==='confirm_intake'?'intake':
              data.next_action==='review_checklist'?'checklist':
              data.next_action==='download_draft'?'package':
              data.next_action==='resolve_documents'?'documents':
              data.next_action==='consult_official'?'handoff':'checklist') as keyof typeof t.stages]}
          </a>
        </div>
      </div>
      {data.checklist.status==='ready_for_user_review'&&
        <div id="case-workflow-checklist" style={{marginTop:20}}>
          <h3>{t.rules}</h3>
          <p>{t.note}</p>
          <p><strong>{t.progress}: {data.checklist.reviewed_count} / {data.checklist.total}</strong></p>
          <ol style={{paddingLeft:22}}>
            {data.checklist.items.map(item=><li key={item.id} style={{marginBottom:15}}>
              <p style={{marginBottom:5}}>{item.description}</p>
              <ul style={{paddingLeft:18,fontSize:12}}>
                {item.evidence.map(ev=><li key={ev.citation_id}>
                  <a href={FIRST_ROUTE_SOURCE_LINKS[ev.source_id as keyof typeof FIRST_ROUTE_SOURCE_LINKS]?.url}
                    target="_blank" rel="noopener noreferrer">
                    {t.source}: {ev.title}
                  </a> · {ev.reviewed_at.slice(0,10)}
                  {ev.archived_reference&&<> · <strong>{t.archived}</strong></>}
                </li>)}
              </ul>
              <label style={{display:'flex',alignItems:'center',gap:9,marginTop:8}}>
                <input type="checkbox" disabled={saving||loading}
                  checked={Object.hasOwn(reviewed,item.id)}
                  onChange={e=>void mark(item.id,e.target.checked)}/>
                <span>{t.check}</span>
              </label>
            </li>)}
          </ol>
        </div>}
      <div id="case-workflow-documents" style={{marginTop:18}}>
        <h3>{t.stages.documents}</h3>
        <p>{data.documents.uploaded_count} · {data.documents.reviewed_count} {t.state.user_reviewed_unverified}</p>
        {data.documents.enabled&&privateDocumentsEnabled
          ?<Link className="button button-outline"
            href={'/cases/'+encodeURIComponent(caseId)+'/documents'}>{t.docs}</Link>
          :<p>{t.noDocs}</p>}
      </div>
      <div id="case-workflow-package" style={{marginTop:18}}>
        <h3>{t.package}</h3>
        {data.package.download_allowed
          ?<a className="button button-primary"
             href={'/api/cases/'+encodeURIComponent(caseId)+'/package/pdf'}>
            {t.draft}
          </a>
          :<p>{t.unavailable}</p>}
        <h4 style={{marginTop:16}}>{t.issues}</h4>
        {data.package.outstanding_issues.length>0
          ?<ul>{data.package.outstanding_issues.map(issue=><li key={issue}>
            {PREPARATION_ISSUES[issue as keyof typeof PREPARATION_ISSUES]??issue}
          </li>)}</ul>
          :<p>{t.noIssues}</p>}
      </div>
      <p style={{marginTop:15,fontSize:12}}>{t.warning}</p>
      {notice&&<p role="status">{notice}</p>}
      <button className="button button-outline" type="button"
        style={{marginTop:10}} disabled={loading||saving}
        onClick={()=>setRevision(x=>x+1)}>{t.refresh}</button>
    </>}
  </section>;
}
