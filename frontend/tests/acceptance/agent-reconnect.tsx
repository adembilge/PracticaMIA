import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  AgentProposalPreview, type PendingProposal, type ProposalDecision, type ProposalValue,
} from '../../src/components/AgentProposalPreview';
import {AgentSourceCards, type AgentCitation} from '../../src/components/AgentSourceCards';
import {AgentOfficialHandoff, type OfficialHandoff} from '../../src/components/AgentOfficialHandoff';
import {AgentGoalSelection, type GoalSelection} from '../../src/components/AgentGoalSelection';

type ActiveRun = { thread_id: string; run_id: string; case_id: string | null };
type CaseTask = { case_id: string; label: string; run_id: string | null };
type CaseTaskPage = { items: CaseTask[]; next_case_id: string | null; unbound_run_id: string | null };
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
  const [view, setView] = useState<RunView | null>(null);
  const [reply, setReply] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [staleReply, setStaleReply] = useState(false);
  const [caseTasks, setCaseTasks] = useState<(CaseTaskPage & { threadId: string }) | null>(null);
  const [newTask, setNewTask] = useState<CaseTask | null>(null);
  const [message, setMessage] = useState('');
  const lastMessage = useRef<{ threadId: string; caseId: string; text: string; id: string } | null>(null);
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
      .then(page => { if (!controller.signal.aborted) setRuns(page.items); })
      .catch(() => { if (!controller.signal.aborted) setError('Could not load conversations.'); });
    return () => controller.abort();
  }, []);

  function displayRun(next: RunView) {
    setView(next);
    setReply('');
    setStaleReply(false);
    setNewTask(null);
    setMessage('');
    setCaseTasks(current => {
      if (!current || current.threadId !== next.snapshot.thread_id) return null;
      return activeStatuses.has(next.snapshot.status) ? current : {
        ...current, items: current.items.map(task => task.run_id === next.snapshot.run_id
          ? { ...task, run_id: null } : task),
        unbound_run_id: current.unbound_run_id === next.snapshot.run_id ? null : current.unbound_run_id,
      };
    });
    if (!activeStatuses.has(next.snapshot.status)) {
      setRuns(items => items?.filter(run => run.run_id !== next.snapshot.run_id) ?? null);
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

  async function listCases(after?: string) {
    if (!view || busy) return;
    const threadId = view.snapshot.thread_id;
    setBusy(true);
    setError('');
    try {
      const url = `/api/agent/threads/${threadId}/cases`;
      const page = await request<CaseTaskPage>(after ? `${url}?after_case_id=${after}` : url);
      setCaseTasks(current => ({
        ...page, threadId, items: after && current?.threadId === threadId
          ? [...current.items, ...page.items] : page.items,
      }));
    } catch {
      setError('Could not load cases in this conversation.');
    } finally {
      setBusy(false);
    }
  }

  async function startTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = message.trim();
    if (!view || !newTask || !text || busy) return;
    const threadId = view.snapshot.thread_id;
    const caseId = newTask.case_id;
    const prior = lastMessage.current;
    const id = prior?.threadId === threadId && prior.caseId === caseId && prior.text === text
      ? prior.id : crypto.randomUUID();
    lastMessage.current = { threadId, caseId, text, id };
    setBusy(true);
    setError('');
    try {
      const path = `/api/agent/threads/${threadId}`;
      const response = await fetch(`${path}/messages`, {
        method: 'POST', cache: 'no-store', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_message_id: id, case_id: caseId, language: 'en', text }),
      });
      if (!response.ok) {
        const problem = await response.json();
        if (response.status === 409 && typeof problem.message === 'string') {
          setError(problem.message);
          return;
        }
        throw new Error(`HTTP ${response.status}`);
      }
      const { run_id }: { run_id: string } = await response.json();
      setRuns(current => [
        { thread_id: threadId, run_id, case_id: caseId },
        ...(current ?? []).filter(run => run.run_id !== run_id),
      ]);
      setCaseTasks(current => current && {
        ...current, items: current.items.map(task => task.case_id === caseId ? { ...task, run_id } : task),
      });
      displayRun(await loadRun(`${path}/runs/${run_id}`));
      lastMessage.current = null;
    } catch {
      setError('Could not confirm the new task. Try again.');
    } finally {
      setBusy(false);
    }
  }

  function answer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendReply('answer');
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
      {!runs && !error && <p role="status">Loading conversations…</p>}
      {runs?.length === 0 && <p>No active conversations.</p>}
      {runs && runs.length > 0 && <ul>
        {runs.map(run => {
          const hasOtherTasks = runs.some(other => other.thread_id === run.thread_id && other.run_id !== run.run_id);
          const label = hasOtherTasks
            ? (run.case_id ? `Open saved case task ${run.case_id.slice(0, 8)}` : 'Open unassigned conversation task')
            : 'Open conversation';
          return <li key={run.run_id}>
            <button type="button" disabled={busy} onClick={() => void open(
              `/api/agent/threads/${run.thread_id}/runs/${run.run_id}`,
            )}>{label}</button>
          </li>;
        })}
      </ul>}
      {view && <section aria-label="Conversation" aria-busy={busy}>
        {view.snapshot.thread_id && <button type="button" disabled={busy} aria-expanded={!!caseTasks}
          onClick={() => {
            if (caseTasks) {
              setCaseTasks(null);
              setNewTask(null);
              setMessage('');
            } else {
              void listCases();
            }
          }}>
          Cases in this conversation
        </button>}
        {caseTasks && <section aria-label="Saved case tasks">
          {caseTasks.unbound_run_id && <button type="button"
            disabled={busy || caseTasks.unbound_run_id === view.snapshot.run_id}
            onClick={() => void open(`/api/agent/threads/${caseTasks.threadId}/runs/${caseTasks.unbound_run_id}`)}>
            Open conversation task
          </button>}
          {caseTasks.items.length ? <ul>{caseTasks.items.map(task => <li key={task.case_id}>
            {task.run_id ? <button type="button" disabled={busy || task.run_id === view.snapshot.run_id}
              aria-current={task.run_id === view.snapshot.run_id ? 'true' : undefined}
              onClick={() => void open(`/api/agent/threads/${caseTasks.threadId}/runs/${task.run_id}`)}>
              Open task for {task.label}
            </button> : <button type="button" disabled={busy}
              onClick={() => { setNewTask(task); setMessage(''); }}>Start task for {task.label}</button>}
          </li>)}</ul> : <p>No linked cases.</p>}
          {caseTasks.next_case_id && <button type="button" disabled={busy}
            onClick={() => void listCases(caseTasks.next_case_id ?? undefined)}>More cases</button>}
          {newTask && <form onSubmit={startTask}>
            <label>
              Message for {newTask.label}
              <textarea rows={3} disabled={busy} maxLength={2000} value={message}
                onChange={event => setMessage(event.target.value)} />
            </label>
            <button type="submit" disabled={busy || !message.trim()}>Start task</button>
          </form>}
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
            <p role="status">Approval recorded. The case update is pending.</p>
          ) : <>
            <p role="status">The pending proposal is unavailable.</p>
            <button type="button" disabled={busy} onClick={() => void open(view.url)}>Check status</button>
          </>
        ) : view.snapshot.result ? <div>
          <h2>{view.snapshot.result.next_action?.operation === 'start_new_topic' ? 'Topic changed' : 'Conversation complete'}</h2>
          <p>{view.snapshot.result.explanation}</p>
          {view.snapshot.selected_case && (
            <a href={`/cases/${view.snapshot.selected_case.case_id}${
              view.snapshot.result.next_action?.operation === 'confirm_saved_intake' ? '#case-intake' : ''
            }`}>{view.snapshot.selected_case.label}</a>
          )}
          {view.snapshot.handoff && <AgentOfficialHandoff handoff={view.snapshot.handoff} />}
          <AgentSourceCards runUrl={view.url} citations={view.snapshot.result.citations ?? []} language="en" />
        </div> : view.snapshot.status === 'stopped' ? (
          <div role="status"><h2>Conversation stopped</h2></div>
        ) : view.snapshot.status === 'failed' ? (
          <div role="status">
            <h2>Conversation failed</h2>
            {view.failureRecovery === 'retry_later' && <p>Send your request again later.</p>}
            {view.failureRecovery === 'review_proposal' && <p>Review the case and request a new proposal.</p>}
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
