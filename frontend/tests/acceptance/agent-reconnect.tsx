import { useEffect, useRef, useState, type FormEvent } from 'react';

type ActiveRun = { thread_id: string; run_id: string };
type Snapshot = {
  status: string;
  last_event_seq: number;
  run_revision: number;
  result: { explanation: string } | null;
};
type Question = { question_id: string; text: string; options: string[] };
type RunView = { url: string; snapshot: Snapshot; question: Question | null };

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
  const [choice, setChoice] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const lastReply = useRef<{ questionId: string; revision: number; choice: string; id: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void request<{ items: ActiveRun[] }>('/api/agent/runs/active', { signal: controller.signal })
      .then(page => { if (!controller.signal.aborted) setRuns(page.items); })
      .catch(() => { if (!controller.signal.aborted) setError('Could not load conversations.'); });
    return () => controller.abort();
  }, []);

  async function open(url: string) {
    setBusy(true);
    setError('');
    try {
      setView(await loadRun(url));
      setChoice('');
    } catch {
      setError('Could not open the conversation.');
    } finally {
      setBusy(false);
    }
  }

  async function answer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!view?.question || !choice || busy) return;
    setBusy(true);
    setError('');
    const questionId = view.question.question_id;
    const revision = view.snapshot.run_revision;
    const prior = lastReply.current;
    const id = prior?.questionId === questionId && prior.revision === revision && prior.choice === choice
      ? prior.id : crypto.randomUUID();
    lastReply.current = { questionId, revision, choice, id };
    try {
      await request(`${view.url}/questions/${questionId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_reply_id: id, expected_run_revision: revision, text: choice }),
      });
      setView(await loadRun(view.url));
      setChoice('');
    } catch {
      setError('Could not confirm the reply. Try again.');
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
        {view.question ? <form onSubmit={answer}>
          <fieldset disabled={busy}>
            <legend>{view.question.text}</legend>
            {view.question.options.map(option => <label key={option}>
              <input type="radio" name="reply" value={option}
                checked={choice === option} onChange={() => setChoice(option)} />
              {option}
            </label>)}
          </fieldset>
          <button type="submit" disabled={!choice || busy}>Send reply</button>
        </form> : view.snapshot.result ? <div>
          <h2>Conversation complete</h2>
          <p>{view.snapshot.result.explanation}</p>
        </div> : <>
          <p role="status">Answer in progress.</p>
          <button type="button" disabled={busy} onClick={() => void open(view.url)}>Check status</button>
        </>}
      </section>}
    </div>
  </main>;
}
