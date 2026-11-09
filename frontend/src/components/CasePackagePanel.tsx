'use client';

import {useCallback,useEffect,useState} from 'react';
import {useDemo} from '@/components/DemoProvider';
import {PREPARATION_ISSUES,validPackageManifest}
  from '@/lib/case-package.js';

type SourceEvidence={
  citation_id:string;source_id:string;official_url:string;archived_reference:boolean;
};
type Manifest={
  status:'blocked'|'reviewable_draft';
  download_allowed:boolean;
  case_reference:string;
  generated_at:string;
  confirmed_facts:{field:string;label:string;value:string}[];
  checklist:{id:string;description:string;evidence:SourceEvidence[]}[];
  documents:{number:number;category:string;review_status:string;
    comparisons:{field:string;result:string}[]}[];
  outstanding_issues:string[];
  official_handoff:{anpr_portal:string;milan_service:string;instruction:string};
};
const copy={
  en:{
    title:'Download your preparation draft',
    intro:'An on-demand PDF combining your confirmed example facts, the current signed checklist, document-review status and official handoff links.',
    notConfirmed:'Confirm your case intake above before reviewing the package.',
    checking:'Checking current evidence and case facts…',
    blocked:'The preparation draft cannot be downloaded yet.',
    available:'The reviewable preparation draft can be downloaded.',
    review:'Review package status',
    download:'Download preparation PDF',
    downloading:'Preparing PDF…',
    latest:'Last checked',
    sources:'Source-backed actions',
    docs:'Documents represented in export',
    issues:'Outstanding issues / limitations',
    noIssues:'No issues detected by the limited checks. This is not official validation.',
    none:'No private document review information is included.',
    failure:'Unable to load the package. Sign in again or try later.',
    risk:'This is not an application, verified document dossier, eligibility decision or government submission receipt. Check the current ANPR instructions and required attachments yourself.',
    handoff:'Official handoff',
    anpr:'Open ANPR',
    municipality:'Comune di Milano',
    unavailable:'Package download is unavailable until the signed checklist and case are confirmed.',
    issue:(key:string)=>PREPARATION_ISSUES[key as keyof typeof PREPARATION_ISSUES]??'Manual review required',
  },
  it:{
    title:'Scarica il riepilogo preparatorio',
    intro:'PDF creato dai dati confermati dell’esempio, dalla lista di azioni firmata, dallo stato dei documenti e dai collegamenti ufficiali.',
    notConfirmed:'Conferma prima la raccolta dati della pratica.',
    checking:'Verifica delle fonti e dei dati in corso…',
    blocked:'Il riepilogo non può ancora essere scaricato.',
    available:'Il riepilogo preparatorio è disponibile per il download.',
    review:'Verifica stato del riepilogo',
    download:'Scarica il PDF preparatorio',
    downloading:'Preparazione PDF…',
    latest:'Ultima verifica',
    sources:'Azioni collegate alle fonti',
    docs:'Documenti inclusi nel riepilogo',
    issues:'Questioni aperte e limitazioni',
    noIssues:'Nessun problema rilevato nei controlli limitati. Non è una verifica ufficiale.',
    none:'Non sono incluse informazioni di revisione documentale.',
    failure:'Impossibile caricare il riepilogo. Effettua nuovamente l’accesso o riprova.',
    risk:'Questo documento non è una domanda, un dossier verificato, una decisione di ammissibilità o una ricevuta ufficiale. Controlla personalmente le istruzioni ANPR e gli allegati attuali.',
    handoff:'Invio esclusivamente a cura dell’utente',
    anpr:'Apri ANPR',
    municipality:'Comune di Milano',
    unavailable:'La generazione richiede una pratica confermata e una lista di azioni con fonti approvate.',
    issue:(key:string)=>PREPARATION_ISSUES[key as keyof typeof PREPARATION_ISSUES]??'Revisione manuale necessaria',
  },
};

export function CasePackagePanel({caseId,revision,confirmed}:{
  caseId:string;revision:number;confirmed:boolean;
}) {
  const {locale}=useDemo();
  const t=copy[locale];
  const [manifest,setManifest]=useState<Manifest|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const [refresh,setRefresh]=useState(0);
  const load=useCallback(async(signal?:AbortSignal)=>{
    setLoading(true);setError('');setManifest(null);
    try{
      const response=await fetch('/api/cases/'+caseId+'/package',{
        cache:'no-store',credentials:'same-origin',signal,
      });
      if(!response.ok)throw new Error('Package unavailable');
      const data:unknown=await response.json();
      if(!validPackageManifest(data))throw new Error('Invalid package manifest');
      if(!signal?.aborted)setManifest(data as Manifest);
    }catch{if(!signal?.aborted)setError(copy[locale].failure);}
    finally{if(!signal?.aborted)setLoading(false);}
  },[caseId,locale]);

  useEffect(()=>{
    if(!confirmed){setManifest(null);setError('');return;}
    const controller=new AbortController();
    void load(controller.signal);
    return ()=>controller.abort();
  },[caseId,revision,confirmed,refresh,load]);

  return <section aria-label={t.title} style={{
    marginTop:24,padding:18,border:'1px solid #d6e5e8',borderRadius:12,
  }}>
    <h3 style={{marginTop:0}}>{t.title}</h3>
    <p>{t.intro}</p>
    {!confirmed?<p role="status">{t.notConfirmed}</p>:<>
      {loading&&<p role="status">{t.checking}</p>}
      {error&&<p role="alert">{error}</p>}
      {manifest&&<>
        <p role="status"><strong>{manifest.download_allowed?t.available:t.blocked}</strong></p>
        <p style={{fontSize:12}}>{t.latest}: {new Date(manifest.generated_at).toLocaleString(
          locale==='it'?'it-IT':'en-GB')}</p>
        <p><strong>{t.sources}:</strong> {manifest.checklist.length}</p>
        <p><strong>{t.docs}:</strong> {manifest.documents.length}</p>
        <h4>{t.issues}</h4>
        {manifest.outstanding_issues.length===0?<p>{t.noIssues}</p>:<ul>
          {manifest.outstanding_issues.map(issue=><li key={issue}>{t.issue(issue)}</li>)}
        </ul>}
        {manifest.download_allowed&&
          <a className="button button-primary"
             style={{display:'inline-flex',marginTop:8}}
             href={'/api/cases/'+encodeURIComponent(caseId)+'/package/pdf'}>
            {t.download}
          </a>}
        {!manifest.download_allowed&&<p>{t.unavailable}</p>}
        <h4 style={{marginTop:20}}>{t.handoff}</h4>
        <p><a href={manifest.official_handoff.anpr_portal}
          target="_blank" rel="noopener noreferrer">{t.anpr}</a>
          {' · '}
          <a href={manifest.official_handoff.milan_service}
            target="_blank" rel="noopener noreferrer">{t.municipality}</a></p>
      </>}
      <button type="button" className="button button-outline"
        style={{marginTop:12}} disabled={loading}
        onClick={()=>setRefresh(n=>n+1)}>{t.review}</button>
    </>}
    <p style={{fontSize:12,marginTop:14,opacity:0.84}}>{t.risk}</p>
  </section>;
}
