'use client';

import Link from 'next/link';
import { useEffect, useState, type FormEvent } from 'react';

type BrowserQueueItem = {
  source_id: string;
  title: string;
  version_id: string;
  content_sha256: string;
  official_url: string;
  observed_url: string;
  observed_last_updated: string;
  captured_text_preview: string;
  integrity_verified: boolean;
};
type Props = { configured: boolean; signedIn: boolean };

export function MobileReviewQueue({ configured, signedIn }: Props) {
  const [items, setItems] = useState<BrowserQueueItem[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [attested, setAttested] = useState(false);
  const [reviewNote, setReviewNote] = useState('');
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(Boolean(configured && signedIn));
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!configured || !signedIn) return;
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch('/api/knowledge/review/browser-queue', {
          credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
        });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const data: unknown = await response.json();
        if (!Array.isArray(data) || !data.every((item) =>
          item && typeof item.source_id === 'string' &&
          typeof item.version_id === 'string' &&
          typeof item.content_sha256 === 'string' &&
          typeof item.integrity_verified === 'boolean')) {
          throw new Error('Invalid response');
        }
        setItems(data as BrowserQueueItem[]);
      } catch {
        if (!controller.signal.aborted) {
          setError('Unable to load the review queue. Confirm that your account is an authorized reviewer.');
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [configured, signedIn]);

  const ready = items.filter((item) => item.integrity_verified);
  const canSubmit = selected.length > 0 && selected.length <= 15 && attested &&
    reviewNote.trim().length >= 30 && reviewNote.length <= 450 && !pending;

  function toggle(id: string, value: boolean) {
    setSelected((previous) => value
      ? [...previous.filter((entry) => entry !== id), id]
      : previous.filter((entry) => entry !== id));
    setAttested(false);
    setSuccess('');
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    const subset = items.filter((item) =>
      selected.includes(item.version_id) && item.integrity_verified);
    if (subset.length !== selected.length) return;
    setError('');
    setSuccess('');
    setPending(true);
    try {
      const response = await fetch('/api/knowledge/review/approve-browser-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        cache: 'no-store',
        body: JSON.stringify({
          items: subset.map((item) => ({
            source_id: item.source_id,
            version_id: item.version_id,
            expected_sha256: item.content_sha256,
          })),
          review_note: reviewNote,
          confirmed_source_review: true,
        }),
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const decisions: unknown = await response.json();
      if (!Array.isArray(decisions) || decisions.length !== subset.length ||
        !decisions.every((decision) =>
          decision && decision.version_status === 'approved')) {
        throw new Error('Invalid review result');
      }
      setItems((previous) => previous.filter((item) =>
        !selected.includes(item.version_id)));
      setSuccess(subset.length + ' browser source versions approved and audited.');
      setSelected([]);
      setAttested(false);
      setReviewNote('');
    } catch {
      setError('Approval failed. No batch success was confirmed. Refresh the queue and review any changed versions.');
    } finally {
      setPending(false);
    }
  }

  return <main id="main-content" tabIndex={-1} className="subpage-background">
    <div className="container account-shell">
      <span className="tiny-eyebrow">AUTHORIZED REVIEWER · PREVIEW ONLY</span>
      <h1 className="subpage-title">Official-source review</h1>
      <p className="message-box warning" role="note">
        Browser-rendered articles are not original server-response HTML.
        A passed SHA-256 check proves capture integrity, not that the
        municipality’s requirements are currently applicable.
        This page excludes all PDFs and does not generate embeddings.
      </p>
      {!configured ? <p className="message-box notice">Review is not configured in this environment.</p>
        : !signedIn ? <section className="account-panel">
          <p>Sign in with your reviewer-authorized account.</p>
          <a className="button button-primary" href="/auth/login">Sign in / Accedi</a>
        </section>
          : <section className="account-panel">
            {loading && <p role="status">Loading the official-source review queue…</p>}
            {!loading && !error && items.length === 0 &&
              <p role="status">No pending browser-rendered articles need review.</p>}
            <form onSubmit={(event) => void submit(event)}>
              <div className="review-queue-toolbar">
                <strong>{ready.length} verifiable browser articles</strong>
                <button type="button" className="button button-secondary"
                  disabled={pending || ready.length === 0 || ready.length > 15}
                  onClick={() => {
                    setSelected(ready.map((item) => item.version_id));
                    setAttested(false);
                  }}>
                  Select all for review
                </button>
              </div>
              <div className="review-queue-list">
                {items.map((item) => <article className="review-queue-item" key={item.version_id}>
                  <label className="review-check">
                    <input type="checkbox"
                      checked={selected.includes(item.version_id)}
                      disabled={pending || !item.integrity_verified}
                      onChange={(event) => toggle(item.version_id, event.target.checked)} />
                    <span><strong>{item.title}</strong>
                      <small>Last updated: {item.observed_last_updated}</small>
                    </span>
                  </label>
                  <p>{item.captured_text_preview}</p>
                  <a href={item.observed_url} target="_blank" rel="noopener noreferrer">
                    Check municipality page
                  </a>
                  <p className="review-metadata">Source: {item.source_id}
                    <br />Version: {item.version_id}
                    <br />SHA-256: {item.content_sha256}
                    <br />{item.integrity_verified
                      ? 'Integrity verified · Browser-rendered text'
                      : 'Integrity check failed — approval blocked'}</p>
                </article>)}
              </div>
              {ready.length > 0 && <>
                <label htmlFor="review-note" className="field-label">Review rationale</label>
                <textarea id="review-note" className="input input-textarea"
                  rows={3} minLength={30} maxLength={450}
                  value={reviewNote} disabled={pending}
                  placeholder="Identify the official evidence inspected and explain why these specific versions remain applicable."
                  onChange={(event) => setReviewNote(event.target.value)} />
                <label className="review-attestation">
                  <input type="checkbox" checked={attested} disabled={pending}
                    onChange={(event) => setAttested(event.target.checked)} />
                  <span>I inspected each selected official page, its exact captured
                    content, dates and exceptions, and confirm the versions
                    are suitable for reviewed staging evidence.</span>
                </label>
                <button type="submit" className="button button-primary" disabled={!canSubmit}>
                  {pending ? 'Recording approvals…'
                    : 'Approve ' + selected.length + ' reviewed article(s)'}
                </button>
              </>}
            </form>
            {error && <p role="alert" className="error-text">{error}</p>}
            {success && <p role="status" className="message-box notice">{success}</p>}
          </section>}
      <p className="account-footnote">
        Reviewer actions require a verified Auth0 token and a server-side
        allowlist. No action is available in production.
      </p>
      <Link href="/account" className="back-link">Back to account</Link>
    </div>
  </main>;
}
