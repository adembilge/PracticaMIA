import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  AgentProposalPreview, type PendingProposal, type ProposalDecision, type ProposalValue,
} from '../../src/components/AgentProposalPreview';
import {AgentSourceCards, type AgentCitation} from '../../src/components/AgentSourceCards';
import {AgentOfficialHandoff, type OfficialHandoff} from '../../src/components/AgentOfficialHandoff';
import {AgentGoalSelection, type GoalSelection} from '../../src/components/AgentGoalSelection';
import {CaseIntakePanel} from '../../src/components/CaseIntakePanel';

type ActiveRun = { thread_id: string; run_id: string; case_id: string | null; status?: string };
type SavedRun = ActiveRun & { status: string };
type ConversationCursor = { accepted_at: string; run_id: string };
type ConversationPage = { items: SavedRun[]; next_cursor: ConversationCursor | null };
type HistoryClarification = {
  event_seq: number; question_id: string; question_text: string;
  disposition: ReplyDisposition; reply_text: string | null;
};
type HistoryApproval = {
  event_seq: number; proposal_id: string; field_id: string; proposed_value: string | number | boolean;
  decision: 'accept' | 'correct' | 'reject' | 'cancel' | null;
  corrected_value: string | number | boolean | null;
  applied_operation_id: string | null;
  applied_case_revision: number | null;
};
type HistoryTerminal = {
  type: 'run.failed' | 'run.stopped';
  code?: 'catalogue_unavailable' | 'provider_unavailable' | 'capacity_exceeded'
    | 'internal_error' | 'proposal_outdated';
  retryable?: boolean;
  recovery?: 'retry_later' | 'resume_run' | 'contact_support' | 'review_proposal';
  committed_operation_ids?: string[];
};
type HistoryTurn = {
  run_id: string; case_id: string | null; status: string;
  accepted_revision: number; user_message: string; language: 'en' | 'it';
  answer: { explanation: string } | null;
  clarifications: HistoryClarification[];
  approvals: HistoryApproval[];
  clarification_history_truncated: boolean;
  approval_history_truncated: boolean;
  terminal_event: HistoryTerminal | null;
};
type HistoryPage = { thread_id: string; items: HistoryTurn[]; next_before_revision: number | null };
type HistoryActivity =
  | { kind: 'clarification'; eventSeq: number; data: HistoryClarification }
  | { kind: 'approval'; eventSeq: number; data: HistoryApproval };
function historyActivities(turn: HistoryTurn): HistoryActivity[] {
  return [
    ...turn.clarifications.map(data => ({
      kind: 'clarification' as const, eventSeq: data.event_seq, data,
    })),
    ...turn.approvals.map(data => ({
      kind: 'approval' as const, eventSeq: data.event_seq, data,
    })),
  ].sort((a, b) => a.eventSeq - b.eventSeq);
}
type Snapshot = {
  thread_id: string;
  run_id: string;
  status: string;
  last_event_seq: number;
  run_revision: number;
  pending_proposal?: PendingProposal | null;
  approval_recorded?: boolean;
  handoff?: OfficialHandoff | null;
  goal_selection?: GoalSelection | null;
  selected_case?: {case_id: string; label: string} | null;
  result: {
    explanation: string;
    next_action?: { operation: string | null } | null;
    citations?: AgentCitation[];
  } | null;
};
type Question = {
  question_id: string;
  text: string;
  answer_shape: 'single_choice' | 'free_text';
  options: string[];
  reply_hint?: string | null;
  goal_selection_language?: 'en' | 'it' | null;
  procedure_goal?: GoalSelection | null;
};
type RunView = {
  url: string;
  snapshot: Snapshot;
  question: Question | null;
  failureRecovery?: 'retry_later' | 'review_proposal';
};
type ReplyDisposition = 'answer' | 'unknown' | 'skip' | 'change_topic';
const activeStatuses = new Set(['queued', 'running', 'waiting_for_information', 'waiting_for_approval', 'stopping']);

/** Keep a single latest entry per thread across arbitrary cursor pages. */
function appendDistinctConversations(existing: SavedRun[], page: SavedRun[]): SavedRun[] {
  const seen = new Set(existing.map(run => run.thread_id));
  return [...existing, ...page.filter(run => {
    if (seen.has(run.thread_id) || activeStatuses.has(run.status)) return false;
    seen.add(run.thread_id);
    return true;
  })];
}

function appendActiveRuns(existing: ActiveRun[], page: SavedRun[]): ActiveRun[] {
  const seen = new Set(existing.map(run => run.run_id));
  return [...existing, ...page.filter(run => {
    if (!activeStatuses.has(run.status) || seen.has(run.run_id)) return false;
    seen.add(run.run_id);
    return true;
  })];
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: 'no-store' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function loadRun(url: string): Promise<RunView> {
  const snapshot = await request<Snapshot>(url);
  if (snapshot.status !== 'waiting_for_information' && snapshot.status !== 'failed') {
    return { url, snapshot, question: null };
  }
  const page = await request<{ events: {
    type: string; event_seq: number; question?: Question; recovery?: string; retryable?: boolean;
  }[] }>(
    `${url}/events?after_seq=${snapshot.last_event_seq - 1}&limit=1`,
  );
  const pending = page.events[0];
  if (snapshot.status === 'failed') {
    const failure = pending?.type === 'run.failed' && pending.event_seq === snapshot.last_event_seq ? pending : null;
    const failureRecovery = failure?.recovery === 'review_proposal' ? 'review_proposal'
      : failure?.recovery === 'retry_later' && failure.retryable ? 'retry_later' : undefined;
    return { url, snapshot, question: null, failureRecovery };
  }
  if (
    pending?.type !== 'question.requested' || pending.event_seq !== snapshot.last_event_seq || !pending.question
  ) throw new Error('Pending question changed');
  return { url, snapshot, question: pending.question };
}

export function AgentReconnectFixture() {
  const [runs, setRuns] = useState<ActiveRun[] | null>(null);
  const [savedRuns, setSavedRuns] = useState<SavedRun[] | null>(null);
  const [savedCursor, setSavedCursor] = useState<ConversationCursor | null>(null);
  const [savedPageBusy, setSavedPageBusy] = useState(false);
  const [history, setHistory] = useState<HistoryPage | null>(null);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [view, setView] = useState<RunView | null>(null);
  const [reply, setReply] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [staleReply, setStaleReply] = useState(false);
  const [firstMessage, setFirstMessage] = useState('');
  const [firstLanguage, setFirstLanguage] = useState<'en' | 'it'>('en');
  const lastFirstMessage = useRef<{ threadId: string | null; text: string; language: 'en' | 'it'; id: string } | null>(null);
  const lastReply = useRef<{
    questionId: string;
    revision: number;
    text: string | null;
    disposition: ReplyDisposition;
    id: string;
  } | null>(null);
  const lastDecision = useRef<{
    proposalId: string;
    revision: number;
    decision: ProposalDecision;
    value: ProposalValue | null;
    id: string;
  } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void request<{ items: ActiveRun[] }>('/api/agent/runs/active', { signal: controller.signal })
      .then(page => {
        if (!controller.signal.aborted) setRuns(current => [
          ...page.items, ...(current ?? []).filter(run => !page.items.some(item => item.run_id === run.run_id)),
        ]);
      })
      .catch(() => { if (!controller.signal.aborted) setError('Could not load conversations.'); });
    void request<ConversationPage>('/api/agent/conversations/recent', { signal: controller.signal })
      .then(page => {
        if (!controller.signal.aborted) {
          setSavedRuns(current => appendDistinctConversations(current ?? [], page.items));
          setRuns(current => appendActiveRuns(current ?? [], page.items));
          setSavedCursor(page.next_cursor);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) { setSavedRuns([]); setSavedCursor(null); }
      });
    return () => controller.abort();
  }, []);

  async function loadOlderConversations() {
    if (!savedCursor || savedPageBusy || busy) return;
    const cursor = savedCursor;
    setSavedPageBusy(true);
    setError('');
    try {
      const params = new URLSearchParams({
        before_accepted_at: cursor.accepted_at, before_run_id: cursor.run_id,
      });
      const page = await request<ConversationPage>(
        `/api/agent/conversations/recent?${params.toString()}`,
      );
      setSavedRuns(current => appendDistinctConversations(current ?? [], page.items));
      setRuns(current => appendActiveRuns(current ?? [], page.items));
      setSavedCursor(current => current?.run_id === cursor.run_id
        && current.accepted_at === cursor.accepted_at ? page.next_cursor : current);
    } catch {
      setError('Could not load older conversations. Try again.');
    } finally {
      setSavedPageBusy(false);
    }
  }

  const historyThreadId = view?.snapshot.thread_id;
  const historyRunId = view?.snapshot.run_id;
  const historyStatus = view?.snapshot.status;
  const historyRunRevision = view?.snapshot.run_revision;
  useEffect(() => {
    if (!historyThreadId) {
      setHistory(null);
      return;
    }
    const controller = new AbortController();
    void request<HistoryPage>(`/api/agent/threads/${historyThreadId}/history`, {
      signal: controller.signal,
    }).then(page => {
      if (!controller.signal.aborted) setHistory(page);
    }).catch(() => {
      if (!controller.signal.aborted) setHistory(null);
    });
    return () => controller.abort();
  }, [historyThreadId, historyRunId, historyStatus, historyRunRevision]);

  async function loadEarlierHistory() {
    if (!history?.next_before_revision || historyBusy || busy || !view) return;
    const threadId = view.snapshot.thread_id;
    const before = history.next_before_revision;
    setHistoryBusy(true);
    try {
      const older = await request<HistoryPage>(
        `/api/agent/threads/${threadId}/history?before_revision=${before}`,
      );
      setHistory(current => current && current.thread_id === threadId
        && current.next_before_revision === before ? {
          ...older, items: [...older.items, ...current.items],
        } : current);
    } catch {
      setError('Could not load earlier messages.');
    } finally {
      setHistoryBusy(false);
    }
  }

  function displayRun(next: RunView) {
    setView(next);
    setReply('');
    setStaleReply(false);
    if (!activeStatuses.has(next.snapshot.status)) {
      setRuns(items => items?.filter(run => run.run_id !== next.snapshot.run_id) ?? null);
      setSavedRuns(items => [
        { thread_id: next.snapshot.thread_id, run_id: next.snapshot.run_id,
          case_id: null, status: next.snapshot.status },
        ...(items ?? []).filter(run => run.thread_id !== next.snapshot.thread_id),
      ]);
    }
  }

  async function open(url: string) {
    setBusy(true);
    setError('');
    try {
      displayRun(await loadRun(url));
    } catch {
      setError('Could not open the conversation.');
    } finally {
      setBusy(false);
    }
  }

  async function startConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = firstMessage.trim();
    const threadId = view?.snapshot.thread_id ?? null;
    if (!text || busy || (view && activeStatuses.has(view.snapshot.status))) return;
    const prior = lastFirstMessage.current;
    const id = prior?.threadId === threadId && prior.text === text && prior.language === firstLanguage
      ? prior.id : crypto.randomUUID();
    lastFirstMessage.current = { threadId, text, language: firstLanguage, id };
    setBusy(true);
    setError('');
    try {
      const endpoint = threadId ? `/api/agent/threads/${threadId}/messages` : '/api/agent/conversations';
      const run = await request<{ thread_id?: string; run_id: string }>(endpoint, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_message_id: id, language: firstLanguage, text }),
      });
      const acceptedThreadId = threadId ?? run.thread_id;
      if (!acceptedThreadId) throw new Error('Missing conversation ID');
      setRuns(current => [
        { thread_id: acceptedThreadId, run_id: run.run_id, case_id: null },
        ...(current ?? []).filter(item => item.run_id !== run.run_id),
      ]);
      setSavedRuns(current => current?.filter(item => item.thread_id !== acceptedThreadId) ?? null);
      displayRun(await loadRun(`/api/agent/threads/${acceptedThreadId}/runs/${run.run_id}`));
      setFirstMessage('');
      lastFirstMessage.current = null;
    } catch {
      setError(firstLanguage === 'it' ? 'Impossibile confermare il nuovo messaggio. Riprova.'
        : 'Could not confirm the new message. Try again.');
    } finally {
      setBusy(false);
    }
  }

  async function sendReply(disposition: ReplyDisposition) {
    const text = disposition === 'answer' ? reply.trim() : null;
    if (!view?.question || text === '' || busy || staleReply) return;
    setBusy(true);
    setError('');
    const questionId = view.question.question_id;
    const revision = view.snapshot.run_revision;
    const prior = lastReply.current;
    const id = prior?.questionId === questionId && prior.revision === revision &&
      prior.text === text && prior.disposition === disposition
      ? prior.id : crypto.randomUUID();
    lastReply.current = { questionId, revision, text, disposition, id };
    try {
      const response = await fetch(`${view.url}/questions/${questionId}/reply`, {
        method: 'POST',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_reply_id: id, expected_run_revision: revision, disposition, text }),
      });
      if (response.status === 409) {
        const problem = await response.json().catch(() => null);
        if (problem?.code === 'conversation_busy') {
          setError(problem.message);
          return;
        }
        lastReply.current = null;
        setReply('');
        setStaleReply(true);
        try {
          displayRun(await loadRun(view.url));
          setError('This reply was rejected because the conversation changed. Review its current status.');
        } catch {
          setError('This reply was rejected because the conversation changed. Check status to reload it.');
        }
        return;
      }
      if (response.status === 422) {
        const problem = await response.json();
        if (['invalid_reply', 'invalid_request'].includes(problem?.code) && typeof problem.message === 'string') {
          setError(problem.message);
          return;
        }
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      displayRun(await loadRun(view.url));
    } catch {
      setError('Could not confirm the reply. Try again.');
    } finally {
      setBusy(false);
    }
  }

  async function decideProposal(decision: ProposalDecision, value: ProposalValue | null = null) {
    const proposal = view?.snapshot.pending_proposal;
    if (!view || !proposal || busy || staleReply) return;
    setBusy(true);
    setError('');
    const revision = view.snapshot.run_revision;
    const prior = lastDecision.current;
    const id = prior?.proposalId === proposal.proposal_id && prior.revision === revision &&
      prior.decision === decision && prior.value === value ? prior.id : crypto.randomUUID();
    lastDecision.current = {proposalId: proposal.proposal_id, revision, decision, value, id};
    try {
      const response = await fetch(`${view.url}/proposals/${proposal.proposal_id}/decision`, {
        method: 'POST',
        cache: 'no-store',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          decision, corrected_value: value, client_decision_id: id, expected_run_revision: revision,
          expected_case_revision: proposal.expected_case_revision,
        }),
      });
      if (response.status === 409) {
        lastDecision.current = null;
        setStaleReply(true);
        displayRun(await loadRun(view.url));
        setError('The proposal changed or expired. Review its current status.');
        return;
      }
      if (response.status === 422) {
        setError('Enter a supported value for the proposed field.');
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      displayRun(await loadRun(view.url));
    } catch {
      setError('Could not confirm the decision. Try again.');
    } finally {
      setBusy(false);
    }
  }

  async function stop() {
    if (!view || busy || staleReply || !activeStatuses.has(view.snapshot.status)) return;
    setBusy(true);
    setError('');
    try {
      const response = await fetch(`${view.url}/stop`, {
        method: 'POST',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expected_run_revision: view.snapshot.run_revision }),
      });
      if (response.status === 409) {
        displayRun(await loadRun(view.url));
        setError('The conversation changed. Review its current status.');
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const snapshot: Snapshot = await response.json();
      displayRun({ url: view.url, snapshot, question: null });
    } catch {
      setError('Could not confirm the stop. Try again.');
    } finally {
      setBusy(false);
    }
  }

  const goalLanguage = view?.question?.goal_selection_language;
  const replyLanguage = goalLanguage ?? view?.question?.procedure_goal?.language;
  const replyAction = goalLanguage === 'it' ? 'Inizia con questa pratica'
    : goalLanguage === 'en' ? 'Start with this task'
    : replyLanguage === 'it' ? 'Invia risposta' : 'Send reply';

  return <main className="case-page" id="main-content">
    <div className="container account-shell">
      <h1>Active conversations</h1>
      {error && <p role="alert">{error}</p>}
      <form aria-label={view ? (firstLanguage === 'it' ? 'Continua conversazione' : 'Continue conversation')
        : (firstLanguage === 'it' ? 'Nuova conversazione' : 'New conversation')}
        onSubmit={startConversation}>
        <label htmlFor="agent-first-language">Language / Lingua</label>
        <select id="agent-first-language" value={firstLanguage} disabled={busy}
          onChange={event => setFirstLanguage(event.target.value === 'it' ? 'it' : 'en')}>
          <option value="en">English</option><option value="it">Italiano</option>
        </select>
        <label htmlFor="agent-first-message">
          {firstLanguage === 'it' ? 'Che pratica vuoi fare?' : 'What would you like help with?'}
        </label>
        <textarea id="agent-first-message" className="input input-textarea" maxLength={2000}
          value={firstMessage} disabled={busy} onChange={event => setFirstMessage(event.target.value)} />
        <button type="submit" disabled={busy || !firstMessage.trim() ||
          !!(view && activeStatuses.has(view.snapshot.status))}>
          {firstLanguage === 'it' ? 'Invia messaggio' : 'Send message'}
        </button>
      </form>
      {!runs && !error && <p role="status">Loading conversations…</p>}
      {runs?.length === 0 && <p>No active conversations.</p>}
      {runs && runs.length > 0 && <ul>
        {runs.map(run => {
          const label = 'Open conversation';
          return <li key={run.run_id} data-active-run-id={run.run_id}>
            <button type="button" disabled={busy} onClick={() => void open(
              `/api/agent/threads/${run.thread_id}/runs/${run.run_id}`,
            )}>{label}</button>
          </li>;
        })}
      </ul>}
      {savedRuns && (savedCursor || savedRuns.some(
        run => !runs?.some(active => active.thread_id === run.thread_id),
      )) && <section aria-label="Past conversations">
        <h2>Past conversations</h2>
        <ul>{savedRuns.filter(run => !runs?.some(active => active.thread_id === run.thread_id))
          .map(run => <li key={run.thread_id} data-conversation-thread={run.thread_id}>
          <button type="button" disabled={busy} onClick={() => void open(
            `/api/agent/threads/${run.thread_id}/runs/${run.run_id}`,
          )}>Open completed conversation</button>
        </li>)}</ul>
        {savedCursor && <button type="button" disabled={busy || savedPageBusy}
          onClick={() => void loadOlderConversations()}>Older conversations</button>}
      </section>}
      {view && <section aria-label="Conversation" aria-busy={busy}>
        {history?.thread_id === view.snapshot.thread_id && <section aria-label="Conversation history">
          {history.next_before_revision && <button type="button" disabled={busy || historyBusy}
            onClick={() => void loadEarlierHistory()}>Earlier messages</button>}
          {history.items.map(turn => <article key={turn.run_id}>
            <p><strong>You:</strong> {turn.user_message}</p>
            {historyActivities(turn).map(entry => entry.kind === 'clarification' ? (
              <div key={`q-${entry.data.question_id}`}>
              <p><strong>PracticaMIA:</strong> <span>{entry.data.question_text}</span></p>
              {entry.data.disposition === 'answer' ? (
                <p><strong>You:</strong> <span>{entry.data.reply_text}</span></p>
              ) : (
                <p><strong>{turn.language === 'it' ? 'Azione:' : 'Action:'}</strong> <span>{
                  entry.data.disposition === 'unknown'
                    ? (turn.language === 'it' ? 'Non lo so' : "I don't know")
                    : entry.data.disposition === 'skip'
                      ? (turn.language === 'it' ? 'Saltato' : 'Skipped')
                      : (turn.language === 'it' ? 'Argomento cambiato' : 'Changed topic')
                }</span></p>
              )}
              </div>
            ) : (
              <section key={`a-${entry.data.proposal_id}`}
              aria-label={`Review history for ${entry.data.field_id}`}>
              <p><strong>{turn.language === 'it' ? 'Modifica proposta:' : 'Proposed change:'}</strong>{' '}
                {entry.data.field_id}: <span>{String(entry.data.proposed_value)}</span></p>
              {entry.data.decision === 'correct' && <p>
                {turn.language === 'it' ? 'Correzione richiesta:' : 'Correction requested:'}{' '}
                <span>{String(entry.data.corrected_value)}</span>.{' '}
                {turn.language === 'it' ? 'Non salvata.' : 'Not saved.'}
              </p>}
              {entry.data.decision === 'reject' && <p>
                {turn.language === 'it' ? 'Rifiutata; nessuna modifica salvata.' : 'Rejected; no change saved.'}
              </p>}
              {entry.data.decision === 'cancel' && <p>
                {turn.language === 'it' ? 'Annullata; nessuna modifica salvata.' : 'Cancelled; no change saved.'}
              </p>}
              {entry.data.decision === null && <p>
                {turn.language === 'it' ? 'In attesa di una decisione.' : 'Awaiting a decision.'}
              </p>}
              {entry.data.decision === 'accept' && (
                entry.data.applied_operation_id && entry.data.applied_case_revision ? <p role="status">
                  {turn.language === 'it' ? 'Salvata nel caso' : 'Saved to case'}{' '}
                  ({turn.language === 'it' ? 'revisione' : 'revision'}{' '}
                  <span>{entry.data.applied_case_revision}</span>).
                </p> : <p role="status">
                  {turn.language === 'it'
                    ? 'Accettata; nessun salvataggio confermato.'
                    : 'Accepted; no saved update confirmed.'}
                </p>
              )}
              </section>
            ))}
            {(turn.clarification_history_truncated || turn.approval_history_truncated) && <p role="status">
              Earlier steps in this turn are available in the run event history.
            </p>}
            {turn.terminal_event?.type === 'run.failed' && <p role="status">
              {turn.language === 'it' ? 'Tentativo non riuscito.' : 'This attempt failed.'}{' '}
              {turn.terminal_event.recovery === 'review_proposal'
                ? (turn.language === 'it' ? 'Controlla la proposta prima di riprovare.'
                  : 'Review the proposal before trying again.')
                : turn.terminal_event.retryable
                  ? (turn.language === 'it' ? 'Puoi inviare di nuovo la richiesta nella chat.'
                    : 'You can send a new message in this chat to retry.')
                  : (turn.language === 'it' ? 'Controlla lo stato prima di riprovare.'
                    : 'Review the current state before trying again.')}
            </p>}
            {turn.terminal_event?.type === 'run.stopped' && <p role="status">
              {turn.terminal_event.committed_operation_ids?.length
                ? (turn.language === 'it'
                  ? `Conversazione interrotta; ${turn.terminal_event.committed_operation_ids.length} modifica già salvata.`
                  : `Conversation stopped; ${turn.terminal_event.committed_operation_ids.length} earlier change already saved.`)
                : (turn.language === 'it'
                  ? 'Conversazione interrotta; nessuna modifica salvata confermata.'
                  : 'Conversation stopped; no confirmed changes.')}
            </p>}
            {turn.answer && turn.run_id !== view.snapshot.run_id && <p>
              <strong>PracticaMIA:</strong> <span>{turn.answer.explanation}</span>
            </p>}
          </article>)}
        </section>}
        {view.snapshot.goal_selection && <AgentGoalSelection selection={view.snapshot.goal_selection} />}
        {staleReply ? (
          <button type="button" disabled={busy} onClick={() => void open(view.url)}>Check status</button>
        ) : view.question ? <form onSubmit={answer} lang={replyLanguage ?? undefined}>
          <fieldset disabled={busy} aria-describedby={view.question.reply_hint ? 'reply-hint' : undefined}>
            <legend>{view.question.text}</legend>
            {view.question.reply_hint && <p id="reply-hint">{view.question.reply_hint}</p>}
            {view.question.answer_shape === 'single_choice' ? view.question.options.map(option => <label key={option}>
              <input type="radio" name="reply" value={option}
                checked={reply === option} onChange={() => setReply(option)} />
              {option}
            </label>) : <label>
              {replyLanguage === 'it' ? 'La tua risposta' : 'Your reply'}
              <textarea name="reply" rows={3} maxLength={2000} value={reply}
                onChange={event => setReply(event.target.value)} />
            </label>}
          </fieldset>
          <button type="submit" disabled={!reply.trim() || busy}>{replyAction}</button>
          <button type="button" disabled={busy} onClick={() => void sendReply('unknown')}>
            {replyLanguage === 'it' ? 'Non lo so' : 'I don’t know'}
          </button>
          <button type="button" disabled={busy} onClick={() => void sendReply('skip')}>
            {replyLanguage === 'it' ? 'Salta per ora' : 'Skip for now'}
          </button>
          <button type="button" disabled={busy} onClick={() => void sendReply('change_topic')}>
            {replyLanguage === 'it' ? 'Cambia argomento' : 'Change topic'}
          </button>
        </form> : view.snapshot.status === 'waiting_for_approval' ? (
          view.snapshot.pending_proposal ? (
            <AgentProposalPreview key={view.snapshot.pending_proposal.proposal_id}
              proposal={view.snapshot.pending_proposal} language="en" busy={busy}
              onDecision={(decision, value) => void decideProposal(decision, value)} />
          ) : view.snapshot.approval_recorded ? (
            <p role="status">Approval recorded. The change is pending.</p>
          ) : <>
            <p role="status">The pending proposal is unavailable.</p>
            <button type="button" disabled={busy} onClick={() => void open(view.url)}>Check status</button>
          </>
        ) : view.snapshot.result ? <div>
          <h2>{view.snapshot.result.next_action?.operation === 'start_new_topic' ? 'Topic changed' : 'Conversation complete'}</h2>
          <p>{view.snapshot.result.explanation}</p>
          {view.snapshot.selected_case && (
            view.snapshot.result.next_action?.operation === 'confirm_saved_intake' ? (
              <section aria-label="In-chat information confirmation">
                <CaseIntakePanel key={view.snapshot.selected_case.case_id}
                  caseId={view.snapshot.selected_case.case_id} />
                <p role="status">
                  After confirming, send another message in this chat to recheck the current filing step.
                  Confirmation alone does not approve eligibility or submit anything officially.
                </p>
              </section>
            ) : <p><strong>Current topic:</strong> {view.snapshot.selected_case.label}</p>
          )}
          {view.snapshot.handoff && <AgentOfficialHandoff handoff={view.snapshot.handoff} />}
          <AgentSourceCards runUrl={view.url} citations={view.snapshot.result.citations ?? []} language="en" />
        </div> : view.snapshot.status === 'stopped' ? (
          <div role="status"><h2>Conversation stopped</h2></div>
        ) : view.snapshot.status === 'failed' ? (
          <div role="status">
            <h2>Conversation failed</h2>
            {view.failureRecovery === 'retry_later' && <p>Send your request again later.</p>}
            {view.failureRecovery === 'review_proposal' && <p>Review the pending change and request a new proposal.</p>}
          </div>
        ) : <>
          <p role="status">Answer in progress.</p>
          <button type="button" disabled={busy} onClick={() => void open(view.url)}>Check status</button>
        </>}
        {!staleReply && activeStatuses.has(view.snapshot.status) && (
          <button type="button" disabled={busy} onClick={() => void stop()}>Stop conversation</button>
        )}
      </section>}
    </div>
  </main>;
}
