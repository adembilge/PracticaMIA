import { useEffect, useRef, useState, type FormEvent } from 'react';

type ActiveRun = { thread_id: string; run_id: string };
type Snapshot = {
  run_id: string;
  status: string;
  last_event_seq: number;
  run_revision: number;
  result: { explanation: string; next_action?: { operation: string | null } | null } | null;
};
type Question = {
  question_id: string;
  text: string;
  answer_shape: 'single_choice' | 'free_text';
  options: string[];
  reply_hint?: string | null;
};
type RunView = { url: string; snapshot: Snapshot; question: Question | null };
type ReplyDisposition = 'answer' | 'unknown' | 'skip' | 'change_topic';
const activeStatuses = new Set(['queued', 'running', 'waiting_for_information', 'waiting_for_approval', 'stopping']);

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: 'no-store' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function loadRun(url: string): Promise<RunView> {
  const snapshot = await request<Snapshot>(url);
  if (snapshot.status !== 'waiting_for_information') return { url, snapshot, question: null };
  const page = await request<{ events: { type: string; event_seq: number; question?: Question }[] }>(
    `${url}/events?after_seq=${snapshot.last_event_seq - 1}&limit=1`,
  );
  const pending = page.events[0];
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
        {staleReply ? (
          <button type="button" disabled={busy} onClick={() => void open(view.url)}>Check status</button>
        ) : view.question ? <form onSubmit={answer}>
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
          <button type="submit" disabled={!reply.trim() || busy}>Send reply</button>
          <button type="button" disabled={busy} onClick={() => void sendReply('unknown')}>I don’t know</button>
          <button type="button" disabled={busy} onClick={() => void sendReply('skip')}>Skip for now</button>
          <button type="button" disabled={busy} onClick={() => void sendReply('change_topic')}>Change topic</button>
        </form> : view.snapshot.result ? <div>
          <h2>{view.snapshot.result.next_action?.operation === 'start_new_topic' ? 'Topic changed' : 'Conversation complete'}</h2>
          <p>{view.snapshot.result.explanation}</p>
        </div> : view.snapshot.status === 'stopped' ? (
          <div role="status"><h2>Conversation stopped</h2></div>
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
