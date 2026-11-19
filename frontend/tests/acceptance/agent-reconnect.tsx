import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  AgentProposalPreview, type PendingProposal, type ProposalDecision, type ProposalValue,
} from '../../src/components/AgentProposalPreview';
import {AgentSourceCards, type AgentCitation} from '../../src/components/AgentSourceCards';
import {AgentOfficialHandoff, type OfficialHandoff} from '../../src/components/AgentOfficialHandoff';
import {AgentGoalSelection, type GoalSelection} from '../../src/components/AgentGoalSelection';

type ActiveRun = { thread_id: string; run_id: string };
type Snapshot = {
  run_id: string;
  status: string;
  last_event_seq: number;
  run_revision: number;
  pending_proposal?: PendingProposal | null;
  approval_recorded?: boolean;
  handoff?: OfficialHandoff | null;
  goal_selection?: GoalSelection | null;
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
  const replyAction = goalLanguage === 'it' ? 'Inizia con questa pratica'
    : goalLanguage === 'en' ? 'Start with this task' : 'Send reply';

  return <main className="case-page" id="main-content">
    <div className="container account-shell">
      <h1>Active conversations</h1>
      {error && <p role="alert">{error}</p>}
      {!runs && !error && <p role="status">Loading conversations…</p>}
      {runs?.length === 0 && <p>No active conversations.</p>}
      {runs && runs.length > 0 && <ul>
        {runs.map(run => <li key={run.run_id}>
          <button type="button" disabled={busy} onClick={() => void open(
            `/api/agent/threads/${run.thread_id}/runs/${run.run_id}`,
          )}>Open conversation</button>
        </li>)}
      </ul>}
      {view && <section aria-label="Conversation" aria-busy={busy}>
        {view.snapshot.goal_selection && <AgentGoalSelection selection={view.snapshot.goal_selection} />}
        {staleReply ? (
          <button type="button" disabled={busy} onClick={() => void open(view.url)}>Check status</button>
        ) : view.question ? <form onSubmit={answer} lang={goalLanguage ?? undefined}>
          <fieldset disabled={busy} aria-describedby={view.question.reply_hint ? 'reply-hint' : undefined}>
            <legend>{view.question.text}</legend>
            {view.question.reply_hint && <p id="reply-hint">{view.question.reply_hint}</p>}
            {view.question.answer_shape === 'single_choice' ? view.question.options.map(option => <label key={option}>
              <input type="radio" name="reply" value={option}
                checked={reply === option} onChange={() => setReply(option)} />
              {option}
            </label>) : <label>
              Your reply
              <textarea name="reply" rows={3} maxLength={2000} value={reply}
                onChange={event => setReply(event.target.value)} />
            </label>}
          </fieldset>
          <button type="submit" disabled={!reply.trim() || busy}>{replyAction}</button>
          <button type="button" disabled={busy} onClick={() => void sendReply('unknown')}>
            {goalLanguage === 'it' ? 'Non lo so' : 'I don’t know'}
          </button>
          <button type="button" disabled={busy} onClick={() => void sendReply('skip')}>
            {goalLanguage === 'it' ? 'Salta per ora' : 'Skip for now'}
          </button>
          <button type="button" disabled={busy} onClick={() => void sendReply('change_topic')}>
            {goalLanguage === 'it' ? 'Cambia argomento' : 'Change topic'}
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
