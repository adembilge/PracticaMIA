'use client';

import {useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent} from 'react';
import {AgentSourceCards, type AgentCitation} from '@/components/AgentSourceCards';
import {AgentOfficialHandoff, type OfficialHandoff} from '@/components/AgentOfficialHandoff';
import {CaseIntakePanel} from '@/components/CaseIntakePanel';
import styles from './SingleChatWorkspace.module.css';

type Language = 'en' | 'it';
type Ref = {thread_id: string; run_id: string; status?: string};
type Cursor = {accepted_at: string; run_id: string};
type Page = {items: Ref[]; next_cursor: Cursor | null};
type Clarification = {
  event_seq: number; question_id: string; question_text: string;
  disposition: 'answer' | 'unknown' | 'skip' | 'change_topic';
  reply_text: string | null;
};
type Approval = {
  event_seq: number; proposal_id: string; field_id: string;
  proposed_value: string | number | boolean; decision: string | null;
  corrected_value: string | number | boolean | null;
  applied_operation_id: string | null;
};
type Turn = {
  run_id: string; user_message: string; language: Language;
  answer: {explanation: string} | null;
  clarifications: Clarification[]; approvals: Approval[];
  terminal_event: {type: string; code?: string; committed_operation_ids?: string[]} | null;
};
type History = {thread_id: string; items: Turn[]; next_before_revision: number | null};
type Question = {
  question_id: string; text: string; answer_shape: 'single_choice' | 'free_text';
  options: string[]; reply_hint?: string | null;
};
type Proposal = {
  proposal_id: string; field_id: string; previous_value: string | number | boolean | null;
  proposed_value: string | number | boolean; rationale: string;
  expected_case_revision: number;
};
type Snapshot = {
  thread_id: string; run_id: string; status: string; last_event_seq: number;
  run_revision: number; result: {
    explanation: string; citations?: AgentCitation[];
    next_action?: {operation: string | null} | null;
  } | null;
  pending_proposal?: Proposal | null;
  approval_recorded?: boolean;
  selected_case?: {case_id: string; label: string} | null;
  handoff?: OfficialHandoff | null;
};
type View = {snapshot: Snapshot; question: Question | null};
type ReplyDisposition = 'answer' | 'unknown' | 'skip' | 'change_topic';

const active = new Set(['queued','running','waiting_for_information','waiting_for_approval','stopping']);
const pending = new Set(['queued','running','stopping']);
const i18n = {
  en: {
    newChat:'New chat', history:'Conversations', older:'Older conversations',
    welcome:'How can I help?', intro:'Ask about Italian administrative procedures. We will clarify what is needed, with reviewed sources where available.',
    placeholder:'Message PracticaMIA', send:'Send', sending:'Sending…',
    signIn:'Sign in', unavailable:'The conversational service is not available in this Preview environment.',
    working:'Request received. Checking its status…', refresh:'Check status',
    stop:'Stop', noHistory:'No conversations yet', noAnswer:'No verified answer is available yet.',
    question:'A detail to clarify', reply:'Send answer', unknown:'I do not know', skip:'Skip for now',
    changeTopic:'Change topic', review:'Review suggested change', confirm:'Accept',
    correct:'Correct value', reject:'Reject', cancel:'Cancel',
    existing:'Previous', proposed:'Proposed', reason:'Reason', saved:'Update was committed.',
    accepted:'Decision recorded. No saved update is confirmed yet.',
    error:'Could not confirm the action. Review the conversation and retry.',
    disclosure:'Independent assistance, not an official government service. Never share passwords or identity documents in the message.',
    account:'Account', signOut:'Sign out', empty:'Start with a question; there is no case to create.',
    doc:'Document upload will be available only after privacy review.',
    retry:'The conversation changed. Open its latest state before continuing.',
    stopped:'This attempt stopped. Previously confirmed updates remain recorded.',
    failed:'The requested operation could not be verified.',
    pendingReview:'Approval status is pending. No write has been confirmed.',
    current:'Current topic', olderTurns:'Earlier messages',
  },
  it: {
    newChat:'Nuova chat', history:'Conversazioni', older:'Conversazioni precedenti',
    welcome:'Come posso aiutarti?', intro:'Chiedi informazioni sulle procedure amministrative italiane. Chiariremo i dettagli e useremo le fonti revisionate disponibili.',
    placeholder:'Scrivi a PracticaMIA', send:'Invia', sending:'Invio…',
    signIn:'Accedi', unavailable:'Il servizio conversazionale non è disponibile in questo ambiente Preview.',
    working:'Richiesta ricevuta. Verifica dello stato…', refresh:'Controlla lo stato',
    stop:'Interrompi', noHistory:'Nessuna conversazione', noAnswer:'Non è ancora disponibile una risposta verificata.',
    question:'Un dettaglio da chiarire', reply:'Invia risposta', unknown:'Non lo so', skip:'Salta per ora',
    changeTopic:'Cambia argomento', review:'Esamina la modifica proposta', confirm:'Accetta',
    correct:'Correggi valore', reject:'Rifiuta', cancel:'Annulla',
    existing:'Precedente', proposed:'Proposto', reason:'Motivo', saved:'Modifica salvata.',
    accepted:'Decisione registrata. Nessun salvataggio confermato.',
    error:'Impossibile confermare l’azione. Controlla la conversazione e riprova.',
    disclosure:'Assistenza indipendente, non è un servizio governativo. Non condividere password o documenti di identità nei messaggi.',
    account:'Account', signOut:'Esci', empty:'Inizia con una domanda; non serve creare una pratica.',
    doc:'Il caricamento dei documenti sarà disponibile dopo la revisione della privacy.',
    retry:'La conversazione è cambiata. Apri lo stato aggiornato per continuare.',
    stopped:'Tentativo interrotto. Le modifiche già confermate rimangono registrate.',
    failed:'Impossibile verificare l’operazione richiesta.',
    pendingReview:'Approvazione in sospeso. Nessuna scrittura confermata.',
    current:'Richiesta attuale', olderTurns:'Messaggi precedenti',
  },
} as const;

function url(threadId:string,runId:string) {
  return '/api/agent/threads/' + encodeURIComponent(threadId) + '/runs/' + encodeURIComponent(runId);
}
async function read<T>(path:string, init?:RequestInit):Promise<T> {
  const result=await fetch(path,{...init,cache:'no-store'});
  if(!result.ok) throw new Error('HTTP '+result.status);
  return result.json() as Promise<T>;
}
async function post<T>(path:string,payload:unknown):Promise<T> {
  return read<T>(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
}
async function runView(threadId:string,runId:string):Promise<View> {
  const path=url(threadId,runId);
  const snapshot=await read<Snapshot>(path);
  if(snapshot.status!=='waiting_for_information') return {snapshot,question:null};
  const events=await read<{events:{type:string;event_seq:number;question?:Question}[]}>(
    path+'/events?after_seq='+Math.max(0,snapshot.last_event_seq-1)+'&limit=1');
  const event=events.events[0];
  if(event?.type!=='question.requested'||event.event_seq!==snapshot.last_event_seq||!event.question){
    throw new Error('Pending prompt unavailable');
  }
  return {snapshot,question:event.question};
}
function mergedRefs(a:Ref[],b:Ref[]):Ref[] {
  const found=new Set<string>();
  return [...b,...a].filter(entry=>{
    if(found.has(entry.thread_id))return false;
    found.add(entry.thread_id);return true;
  });
}
function titleFor(turns:Turn[]|undefined,lang:Language):string {
  const first=turns?.[0]?.user_message.trim();
  return first ? first.slice(0,58) : lang==='it'?'Conversazione':'Conversation';
}

export function SingleChatWorkspace({signedIn,configured,displayName}:{
  signedIn:boolean;configured:boolean;displayName:string;
}){
  const [language,setLanguage]=useState<Language>('en');
  const text=i18n[language];
  const [drawer,setDrawer]=useState(false);
  const [refs,setRefs]=useState<Ref[]>([]);
  const [cursor,setCursor]=useState<Cursor|null>(null);
  const [view,setView]=useState<View|null>(null);
  const [history,setHistory]=useState<History|null>(null);
  const [draft,setDraft]=useState('');
  const [reply,setReply]=useState('');
  const [correction,setCorrection]=useState('');
  const [editing,setEditing]=useState(false);
  const [busy,setBusy]=useState(false);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const [blocked,setBlocked]=useState(false);
  const [lastRead,setLastRead]=useState<string|null>(null);
  const retries=useRef<{thread:string|null;text:string;language:Language;id:string}|null>(null);
  const transcript=useRef<HTMLDivElement|null>(null);
  const currentThread=view?.snapshot.thread_id ?? null;
  const currentRun=view?.snapshot.run_id ?? null;
  const inProgress=Boolean(view && active.has(view.snapshot.status));

  const open=useCallback(async(threadId:string,runId:string)=>{
    setBusy(true);setError('');setDrawer(false);
    try{
      const [next,turns]=await Promise.all([
        runView(threadId,runId),
        read<History>('/api/agent/threads/'+threadId+'/history'),
      ]);
      setView(next);setHistory(turns);setReply('');setEditing(false);
      setLastRead(threadId);
    }catch{setError(i18n[language].error)}
    finally{setBusy(false)}
  },[language]);

  useEffect(()=>{
    if(!signedIn||!configured)return;
    let alive=true;
    setLoading(true);
    Promise.all([
      read<Page>('/api/agent/conversations/recent'),
      read<Page>('/api/agent/runs/active'),
    ]).then(async([recent,working])=>{
      if(!alive)return;
      const all=mergedRefs(recent.items,working.items);
      setRefs(all);setCursor(recent.next_cursor);
      if(!all.length)return;
      // Do not open another user's conversation from local persistence.
      const first=all[0];
      const [snapshot,turns]=await Promise.all([
        runView(first.thread_id,first.run_id),
        read<History>('/api/agent/threads/'+first.thread_id+'/history'),
      ]);
      if(alive){setView(snapshot);setHistory(turns);setLastRead(first.thread_id);}
    }).catch(()=>{if(alive)setBlocked(true)})
      .finally(()=>{if(alive)setLoading(false)});
    return()=>{alive=false};
  },[signedIn,configured]);

  const refresh=useCallback(async()=>{
    if(!view)return;
    try {
      const next=await runView(view.snapshot.thread_id,view.snapshot.run_id);
      const turns=await read<History>('/api/agent/threads/'+next.snapshot.thread_id+'/history');
      setView(next);setHistory(turns);setError('');
      if(!active.has(next.snapshot.status))setRefs(old=>mergedRefs(old,[{
        thread_id:next.snapshot.thread_id,run_id:next.snapshot.run_id,status:next.snapshot.status,
      }]));
    }catch{setError(i18n[language].error)}
  },[view,language]);

  useEffect(()=>{
    if(!view||!pending.has(view.snapshot.status))return;
    const id=setInterval(()=>{void refresh()},3500);
    return()=>clearInterval(id);
  },[view?.snapshot.thread_id,view?.snapshot.run_id,view?.snapshot.status,refresh]);

  useEffect(()=>{
    transcript.current?.scrollTo({top:transcript.current.scrollHeight,behavior:'smooth'});
  },[history?.items.length,view?.snapshot.status,view?.question?.question_id]);

  async function send(event?:FormEvent<HTMLFormElement>){
    event?.preventDefault();
    const message=draft.trim();
    if(!message||busy||inProgress||!signedIn||!configured||blocked)return;
    const same=retries.current?.thread===currentThread
      && retries.current.text===message&&retries.current.language===language;
    const id=same?retries.current!.id:crypto.randomUUID();
    retries.current={thread:currentThread,text:message,language,id};
    setBusy(true);setError('');
    try{
      const started=await post<{thread_id?:string;run_id:string}>(
        currentThread?'/api/agent/threads/'+currentThread+'/messages':'/api/agent/conversations',
        {client_message_id:id,text:message,language},
      );
      const threadId=started.thread_id??currentThread;
      if(!threadId)throw new Error('Missing conversation ID');
      const entry={thread_id:threadId,run_id:started.run_id,status:'queued'};
      setRefs(old=>mergedRefs(old,[entry]));
      setDraft('');retries.current=null;
      await open(threadId,started.run_id);
    }catch{setError(text.error)}
    finally{setBusy(false)}
  }

  async function answer(disposition:ReplyDisposition){
    if(!view?.question||busy)return;
    const value=disposition==='answer'?reply.trim():null;
    if(disposition==='answer'&&!value)return;
    setBusy(true);setError('');
    try{
      await post(url(view.snapshot.thread_id,view.snapshot.run_id)+'/questions/'+
        view.question.question_id+'/reply',{
          client_reply_id:crypto.randomUUID(),
          expected_run_revision:view.snapshot.run_revision,disposition,text:value,
        });
      setReply('');await open(view.snapshot.thread_id,view.snapshot.run_id);
    }catch{setError(text.retry)}
    finally{setBusy(false)}
  }

  async function decide(decision:'accept'|'correct'|'reject'|'cancel'){
    const proposal=view?.snapshot.pending_proposal;
    if(!proposal||!view||busy)return;
    let value:string|number|boolean|null=null;
    if(decision==='correct'){
      const trimmed=correction.trim();if(!trimmed)return;
      if(typeof proposal.proposed_value==='number'){
        const number=Number(trimmed);if(!Number.isFinite(number))return;value=number;
      }else if(typeof proposal.proposed_value==='boolean'){
        if(trimmed!=='true'&&trimmed!=='false')return;value=trimmed==='true';
      }else value=trimmed;
    }
    setBusy(true);setError('');
    try{
      await post(url(view.snapshot.thread_id,view.snapshot.run_id)+'/proposals/'+
        proposal.proposal_id+'/decision',{
          decision,corrected_value:value,client_decision_id:crypto.randomUUID(),
          expected_run_revision:view.snapshot.run_revision,
          expected_case_revision:proposal.expected_case_revision,
        });
      setEditing(false);await open(view.snapshot.thread_id,view.snapshot.run_id);
    }catch{setError(text.retry)}
    finally{setBusy(false)}
  }

  async function stop(){
    if(!view||busy||!inProgress)return;
    setBusy(true);
    try{
      await post(url(view.snapshot.thread_id,view.snapshot.run_id)+'/stop',{
        expected_run_revision:view.snapshot.run_revision,
      });
      await open(view.snapshot.thread_id,view.snapshot.run_id);
    }catch{setError(text.retry)}
    finally{setBusy(false)}
  }

  async function older(){
    if(!cursor||busy)return;
    setBusy(true);
    try{
      const params=new URLSearchParams({before_accepted_at:cursor.accepted_at,
        before_run_id:cursor.run_id});
      const page=await read<Page>('/api/agent/conversations/recent?'+params);
      setRefs(old=>mergedRefs(old,page.items));setCursor(page.next_cursor);
    }catch{setError(text.error)}finally{setBusy(false)}
  }

  async function olderTurns(){
    if(!view||!history?.next_before_revision||busy)return;
    setBusy(true);
    try {
      const page=await read<History>('/api/agent/threads/'+view.snapshot.thread_id+
        '/history?before_revision='+history.next_before_revision);
      setHistory(old=>old?.thread_id===page.thread_id
        ? {...page,items:[...page.items,...old.items]} : page);
    }catch{setError(text.error)}finally{setBusy(false)}
  }

  function newChat(){
    setView(null);setHistory(null);setDraft('');setReply('');setError('');
    retries.current=null;setDrawer(false);setLastRead(null);
  }

  function keyDown(event:KeyboardEvent<HTMLTextAreaElement>){
    if(event.key==='Enter'&&!event.shiftKey){
      event.preventDefault();void send();
    }
  }
  const all=history?.items??[];
  const currentStatus=view?.snapshot.status;
  const showQuestion=view?.question&&currentStatus==='waiting_for_information';
  const canSend=signedIn&&configured&&!blocked&&!busy&&!inProgress;

  return <main className={styles.shell} id="main-content" data-chat-only="true">
    <a className={styles.skip} href="#chat-composer">{language==='it'?'Vai al messaggio':'Skip to message'}</a>
    <div className={styles.backdrop} data-open={drawer} onClick={()=>setDrawer(false)}/>
    <aside className={styles.sidebar} data-open={drawer} aria-label={text.history}>
      <div className={styles.sideHeader}><strong>practicamia<span>.</span></strong>
        <button type="button" className={styles.close} onClick={()=>setDrawer(false)} aria-label="Close history">×</button>
      </div>
      <button type="button" className={styles.newChat} onClick={newChat}>
        <span aria-hidden="true">＋</span> {text.newChat}
      </button>
      <h2>{text.history}</h2>
      <nav aria-label={text.history}>
        {refs.length===0&&!loading&&<p className={styles.muted}>{text.noHistory}</p>}
        {refs.map((entry,index)=><button
          key={entry.thread_id}
          type="button"
          aria-current={lastRead===entry.thread_id?'page':undefined}
          className={styles.conversation}
          disabled={busy}
          onClick={()=>void open(entry.thread_id,entry.run_id)}>
          <span aria-hidden="true" className={styles.chatIcon}>▤</span>
          <span>{entry.thread_id===history?.thread_id
            ? titleFor(all,language)
            : (language==='it'?'Conversazione ':'Conversation ')+(index+1)}</span>
        </button>)}
      </nav>
      {cursor&&<button type="button" disabled={busy} className={styles.older}
        onClick={()=>void older()}>{text.older}</button>}
      <div className={styles.sideFoot}>
        <span>{displayName||text.account}</span>
        {signedIn&&<a href="/auth/logout">{text.signOut}</a>}
      </div>
    </aside>
    <section className={styles.main} aria-label="PracticaMIA chat">
      <header className={styles.top}>
        <button type="button" className={styles.menu} onClick={()=>setDrawer(true)}
          aria-label={text.history}>☰</button>
        <span className={styles.topTitle}>PracticaMIA <small>Preview</small></span>
        <div className={styles.tools}>
          <button type="button" className={styles.locale} onClick={()=>setLanguage(l=>l==='en'?'it':'en')}>
            {language.toUpperCase()}
          </button>
          <button type="button" className={styles.newTop} onClick={newChat}
            aria-label={text.newChat}>＋</button>
        </div>
      </header>
      <div className={styles.transcript} ref={transcript} aria-live="polite">
        <div className={styles.messages}>
          {!view&&<div className={styles.welcome}>
            <div className={styles.logo} aria-hidden="true">P.</div>
            <h1>{text.welcome}</h1><p>{text.intro}</p>
            {!signedIn&&<a className={styles.signin} href="/auth/login">{text.signIn}</a>}
            {signedIn&&(!configured||blocked)&&
              <p role="status" className={styles.notice}>{text.unavailable}</p>}
          </div>}
          {loading&&<p role="status" className={styles.muted}>Loading conversations…</p>}
          {history?.next_before_revision&&<button type="button" onClick={()=>void olderTurns()}
            className={styles.older} disabled={busy}>{text.olderTurns}</button>}
          {all.map(turn=><div key={turn.run_id} className={styles.turn}>
            <div className={styles.userBubble}><span>{turn.user_message}</span></div>
            {[
              ...(turn.clarifications||[]).map(item=>({kind:'question' as const,seq:item.event_seq,item})),
              ...(turn.approvals||[]).map(item=>({kind:'approval' as const,seq:item.event_seq,item})),
            ].sort((a,b)=>a.seq-b.seq).map(activity=>
              <div className={styles.systemBubble} key={activity.kind+'-'+activity.seq}>
                {activity.kind==='question'?<>
                  <strong>{activity.item.question_text}</strong>
                  <p>{activity.item.disposition==='answer'
                    ? activity.item.reply_text
                    : activity.item.disposition==='unknown'?text.unknown
                    : activity.item.disposition==='skip'?text.skip:text.changeTopic}</p>
                </>:<>
                  <strong>{text.review}: {activity.item.field_id}</strong>
                  <p>{String(activity.item.proposed_value)}</p>
                  {activity.item.applied_operation_id?<p>{text.saved}</p>
                    :<p>{text.accepted}</p>}
                </>}
              </div>
            )}
            {turn.answer&&turn.run_id!==currentRun&&
              <div className={styles.assistantBubble}><div className={styles.avatar}>P.</div>
                <p>{turn.answer.explanation}</p></div>}
            {turn.terminal_event&&<p className={styles.muted}>{turn.terminal_event.type==='run.stopped'
              ?text.stopped:text.failed}</p>}
          </div>)}
          {view&&<div className={styles.assistantBubble}>
            <div className={styles.avatar} aria-hidden="true">P.</div>
            <div className={styles.assistantBody}>
              {view.snapshot.result?.explanation&&<p>{view.snapshot.result.explanation}</p>}
              {pending.has(currentStatus??'')&&<p role="status">{text.working}</p>}
              {currentStatus==='failed'&&<p role="alert">{text.failed}</p>}
              {currentStatus==='stopped'&&<p role="status">{text.stopped}</p>}
              {showQuestion&&<section className={styles.card} aria-label={text.question}>
                <h2>{view.question!.text}</h2>
                {view.question!.reply_hint&&<p>{view.question!.reply_hint}</p>}
                <form onSubmit={event=>{event.preventDefault();void answer('answer')}}>
                  {view.question!.answer_shape==='single_choice'
                    ? <fieldset><legend>{text.question}</legend>{view.question!.options.map(option=>
                      <label key={option} className={styles.option}>
                        <input type="radio" name="reply" value={option} checked={reply===option}
                          disabled={busy} onChange={()=>setReply(option)}/>{option}
                      </label>)}</fieldset>
                    : <label><span>{text.question}</span><textarea value={reply} maxLength={2000}
                      disabled={busy} onChange={event=>setReply(event.target.value)}/></label>}
                  <div className={styles.actions}>
                    <button type="submit" disabled={busy||!reply.trim()}>{text.reply}</button>
                    <button type="button" disabled={busy} onClick={()=>void answer('unknown')}>{text.unknown}</button>
                    <button type="button" disabled={busy} onClick={()=>void answer('skip')}>{text.skip}</button>
                    <button type="button" disabled={busy} onClick={()=>void answer('change_topic')}>{text.changeTopic}</button>
                  </div>
                </form>
              </section>}
              {currentStatus==='waiting_for_approval'&&view.snapshot.pending_proposal&&
                <section className={styles.card} aria-label={text.review}>
                  <h2>{text.review}</h2>
                  <dl><dt>{text.existing}</dt><dd>{String(view.snapshot.pending_proposal.previous_value??'—')}</dd>
                    <dt>{text.proposed}</dt><dd>{String(view.snapshot.pending_proposal.proposed_value)}</dd>
                    <dt>{text.reason}</dt><dd>{view.snapshot.pending_proposal.rationale}</dd></dl>
                  {editing&&<label>{text.correct}<input value={correction} maxLength={300}
                    onChange={event=>setCorrection(event.target.value)} disabled={busy}/></label>}
                  <div className={styles.actions}>
                    {editing?<button type="button" onClick={()=>void decide('correct')}
                      disabled={busy||!correction.trim()}>{text.confirm}</button>:<>
                      <button type="button" disabled={busy} onClick={()=>void decide('accept')}>{text.confirm}</button>
                      <button type="button" disabled={busy}
                        onClick={()=>{setEditing(true);setCorrection(String(view.snapshot.pending_proposal!.proposed_value))}}>
                        {text.correct}</button></>}
                    <button type="button" disabled={busy} onClick={()=>void decide('reject')}>{text.reject}</button>
                    <button type="button" disabled={busy} onClick={()=>void decide('cancel')}>{text.cancel}</button>
                  </div>
                </section>}
              {currentStatus==='waiting_for_approval'&&!view.snapshot.pending_proposal&&
                <p role="status">{text.pendingReview}</p>}
              {view.snapshot.selected_case?.case_id&&view.snapshot.result?.next_action?.operation==='confirm_saved_intake'&&
                <section className={styles.card} aria-label="In-chat information review">
                  <CaseIntakePanel caseId={view.snapshot.selected_case.case_id}/>
                </section>}
              {view.snapshot.handoff&&<div className={styles.card}>
                <AgentOfficialHandoff handoff={view.snapshot.handoff}/></div>}
              {view.snapshot.result?.citations?.length&&<div className={styles.card}>
                <AgentSourceCards runUrl={url(view.snapshot.thread_id,view.snapshot.run_id)}
                  citations={view.snapshot.result.citations} language={language}/></div>}
              {view.snapshot.selected_case&&view.snapshot.result?.next_action?.operation!=='confirm_saved_intake'&&
                <p className={styles.muted}>{text.current}: {view.snapshot.selected_case.label}</p>}
              {view&&(pending.has(currentStatus??'')||currentStatus==='waiting_for_information'
                ||currentStatus==='waiting_for_approval')&&
                <div className={styles.actions}>
                  <button type="button" disabled={busy} onClick={()=>void refresh()}>{text.refresh}</button>
                  {inProgress&&<button type="button" disabled={busy}
                    onClick={()=>void stop()}>{text.stop}</button>}
                </div>}
            </div>
          </div>}
        </div>
      </div>
      {error&&<div role="alert" className={styles.error}>{error}
        <button type="button" onClick={()=>setError('')} aria-label="Dismiss error">×</button></div>}
      <footer className={styles.bottom}>
        <form className={styles.composer} onSubmit={event=>void send(event)}>
          <label className={styles.srOnly} htmlFor="chat-composer">{text.placeholder}</label>
          <textarea id="chat-composer" value={draft} rows={2} maxLength={2000}
            placeholder={text.placeholder} onChange={event=>setDraft(event.target.value)}
            onKeyDown={keyDown} disabled={!canSend}/>
          <div className={styles.composerBar}>
            <button type="button" title={text.doc} aria-label={text.doc}
              className={styles.attachment} disabled>＋</button>
            <span className={styles.charCount}>{draft.length}/2000</span>
            <button type="submit" className={styles.send} disabled={!canSend||!draft.trim()}>
              {busy?text.sending:text.send} <span aria-hidden="true">↑</span>
            </button>
          </div>
        </form>
        <p className={styles.disclosure}>{text.disclosure}</p>
      </footer>
    </section>
  </main>;
}
