'use client';

import { useEffect, useState, type FormEvent } from 'react';

type PendingPdf = {
  source_id: string;
  version_id: string;
  revision: number;
  title: string;
  institution: string;
  official_url: string;
  content_sha256: string;
  source_status: string;
  version_status: string;
  retrieved_at: string;
};
type PdfPreview = PendingPdf & {
  integrity_verified: boolean;
  normalized_text: string;
  passages: { id: string; ordinal: number; content_sha256: string }[];
};
type Props = { signedIn: boolean; configured: boolean };

function isPdf(item: PendingPdf) {
  return /^https:\/\//.test(item.official_url) &&
    /\.pdf(?:\?|$)/i.test(item.official_url) &&
    item.source_status === 'candidate' && item.version_status === 'pending_review';
}

export function PdfReviewPanel({ signedIn, configured }: Props) {
  const [items, setItems] = useState<PendingPdf[]>([]);
  const [loading, setLoading] = useState(Boolean(signedIn && configured));
  const [fetchError, setFetchError] = useState('');
  const [selected, setSelected] = useState<PdfPreview | null>(null);
  const [inspecting, setInspecting] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [attested, setAttested] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [decisionError, setDecisionError] = useState('');
  const [result, setResult] = useState('');

  useEffect(() => {
    if (!signedIn || !configured) return;
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch('/api/knowledge/review/queue', {
          credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
        });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const payload: unknown = await response.json();
        if (!Array.isArray(payload) || !payload.every(item =>
          item && typeof item.source_id === 'string' &&
          typeof item.version_id === 'string' &&
          typeof item.official_url === 'string' &&
          typeof item.content_sha256 === 'string' &&
          typeof item.version_status === 'string' &&
          typeof item.source_status === 'string')) {
          throw new Error('Invalid pending-source queue');
        }
        if (!controller.signal.aborted) {
          setItems((payload as PendingPdf[]).filter(isPdf));
        }
      } catch {
        if (!controller.signal.aborted) {
          setFetchError('Cannot load pending PDF versions. Check your reviewer account and refresh.');
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [configured, signedIn]);

  async function inspect(item: PendingPdf) {
    if (inspecting || submitting) return;
    setSelected(null);
    setNote('');
    setAttested(false);
    setResult('');
    setDecisionError('');
    setInspecting(item.version_id);
    try {
      const response = await fetch('/api/knowledge/review/versions/' +
        encodeURIComponent(item.version_id), {
        credentials: 'same-origin', cache: 'no-store',
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const raw: unknown = await response.json();
      if (!raw || typeof raw !== 'object') throw new Error('Invalid version');
      const full = raw as PdfPreview;
      if (full.version_id !== item.version_id ||
        full.source_id !== item.source_id ||
        full.content_sha256 !== item.content_sha256 ||
        full.official_url !== item.official_url ||
        full.version_status !== 'pending_review' ||
        full.integrity_verified !== true ||
        typeof full.normalized_text !== 'string' ||
        full.normalized_text.length < 1 || full.normalized_text.length > 250000 ||
        !Array.isArray(full.passages) || full.passages.length < 1) {
        throw new Error('Version changed or its integrity check failed');
      }
      setSelected(full);
    } catch {
      setDecisionError('PDF inspection failed or the version changed. It cannot be approved.');
    } finally {
      setInspecting(null);
    }
  }

  const canApprove = selected !== null && attested &&
    note.trim().length >= 30 && note.length <= 450 &&
    !submitting && inspecting === null;

  async function approve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canApprove || !selected) return;
    const reviewed = selected;
    setSubmitting(true);
    setDecisionError('');
    setResult('');
    try {
      const response = await fetch('/api/knowledge/review/versions/' +
        encodeURIComponent(reviewed.version_id) + '/approve', {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          expected_sha256: reviewed.content_sha256,
          review_note: note.trim(),
          confirmed_source_review: true,
        }),
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const decision: unknown = await response.json();
      if (!decision || typeof decision !== 'object') throw new Error('Invalid response');
      const approval = decision as {
        source_id?: unknown; version_id?: unknown;
        version_status?: unknown; audit_id?: unknown;
      };
      if (approval.source_id !== reviewed.source_id ||
        approval.version_id !== reviewed.version_id ||
        approval.version_status !== 'approved' ||
        typeof approval.audit_id !== 'string' || !approval.audit_id) {
        throw new Error('Approval confirmation invalid');
      }
      setItems(previous => previous.filter(item =>
        item.version_id !== reviewed.version_id));
      setSelected(null);
      setAttested(false);
      setNote('');
      setResult('PDF version approved and audited. Audit ID: ' + approval.audit_id);
    } catch {
      setDecisionError('Approval was not confirmed. Refresh the page and inspect the current version before retrying.');
    } finally {
      setSubmitting(false);
    }
  }

  if (!configured || !signedIn) return null;

  return <section className="account-panel" aria-labelledby="pdf-review-heading">
    <h2 id="pdf-review-heading">Pending PDF source review</h2>
    <p>PDF versions use individual approval, not the browser-rendered article queue.
      The exact stored PDF and its extracted text must be inspected before approval.</p>
    <p className="message-box warning">
      Approving an imported public ANPR guide attests to this exact archived
      source version. It does not establish that the guide is the current
      live ANPR form, activate Milan rules, or submit any government document.
    </p>
    {loading && <p role="status">Loading pending PDFs…</p>}
    {!loading && !fetchError && items.length === 0 &&
      <p role="status">No PDF source versions are pending review.</p>}
    {fetchError && <p role="alert" className="error-text">{fetchError}</p>}
    {items.map(item => <article key={item.version_id} className="review-queue-item">
      <h3>{item.title}</h3>
      <p className="review-metadata">Institution: {item.institution}
        <br />Source: {item.source_id}
        <br />Version: {item.version_id}
        <br />SHA-256: {item.content_sha256}
        <br />Status: pending review</p>
      <p>
        <a href={item.official_url} target="_blank" rel="noopener noreferrer">
          Open source PDF for page-by-page inspection
        </a>
      </p>
      <button className="button button-secondary" type="button"
        disabled={Boolean(inspecting) || submitting}
        onClick={() => void inspect(item)}>
        {inspecting === item.version_id ? 'Checking entire source…'
          : selected?.version_id === item.version_id
            ? 'Verified extracted text displayed below'
            : 'Inspect complete extracted PDF text'}
      </button>
      {selected?.version_id === item.version_id && <>
        <section className="review-full-text" aria-label={'Full extracted PDF: ' + item.title}>
          <h4>Complete extracted text ({selected.passages.length} verified passages)</h4>
          <pre>{selected.normalized_text}</pre>
        </section>
        <form onSubmit={(event) => void approve(event)}>
          <label className="field-label" htmlFor="pdf-review-note">
            Your review rationale
          </label>
          <textarea id="pdf-review-note" className="input input-textarea"
            value={note} onChange={event => { setNote(event.target.value); setAttested(false); }}
            minLength={30} maxLength={450} rows={4} disabled={submitting}
            placeholder="Explain what you verified in the exact original PDF, its archive provenance and applicability limits." />
          <label className="review-attestation">
            <input type="checkbox" checked={attested}
              disabled={submitting} onChange={event => setAttested(event.target.checked)} />
            <span>I inspected the linked PDF, the complete stored extracted text
              and its provenance, and approve this exact SHA-256 source version.
              I understand this does not certify the current ANPR requirements.</span>
          </label>
          <button type="submit" className="button button-primary" disabled={!canApprove}>
            {submitting ? 'Recording verified decision…' : 'Approve this inspected PDF version'}
          </button>
        </form>
      </>}
    </article>)}
    {decisionError && <p role="alert" className="error-text">{decisionError}</p>}
    {result && <p role="status" className="message-box notice">{result}</p>}
  </section>;
}
