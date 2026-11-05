'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { type Answer, useDemo } from '@/components/DemoProvider';
import { classifySingleAnswer } from '@/lib/flow.js';
import { firstUnresolvedQuestion, isCaseId, nextScopeAnswers } from '@/lib/case-scope.js';

type StoredCase = {
  id: string;
  procedure: string;
  status: string;
  scope_answers: Answer[];
  created_at: string;
  updated_at: string;
};

type Props = { caseId: string; configured: boolean; signedIn: boolean; assistantEnabled: boolean };
const ANSWERS: Answer[] = ['yes', 'no', 'unsure'];

export function SavedCaseWorkspace({ caseId, configured, signedIn, assistantEnabled }: Props) {
  const router = useRouter();
  const { t, locale } = useDemo();
  const [record, setRecord] = useState<StoredCase | null>(null);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [selected, setSelected] = useState<Answer | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/cases/' + caseId, { cache: 'no-store', signal });
      if (!response.ok) throw new Error('Case unavailable');
      const saved = (await response.json()) as StoredCase;
      if (saved.id !== caseId || !Array.isArray(saved.scope_answers)) throw new Error('Invalid response');
      const index = firstUnresolvedQuestion(saved.scope_answers);
      setRecord(saved);
      setQuestionIndex(index);
      setSelected(saved.scope_answers[index] ?? null);
      setReviewing(saved.status === 'provisionally_in_scope' && saved.scope_answers.length === 5);
    } catch {
      if (!signal?.aborted) setError(t.savedError);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [caseId, t.savedError]);

  useEffect(() => {
    if (!configured || !signedIn || !isCaseId(caseId)) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [caseId, configured, signedIn, load]);

  function openQuestion(index: number, data = record) {
    if (!data) return;
    setQuestionIndex(index);
    setSelected(data.scope_answers[index] ?? null);
    setReviewing(false);
    setError('');
    setNotice('');
  }

  async function saveAnswer() {
    if (!record || !selected || saving) return;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const answers = nextScopeAnswers(record.scope_answers, questionIndex, selected);
      let updated = record;
      if (answers.length !== record.scope_answers.length
        || answers.some((answer, index) => answer !== record.scope_answers[index])) {
        const response = await fetch('/api/cases/' + caseId + '/scope', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ answers }),
        });
        if (!response.ok) throw new Error('Save failed');
        updated = (await response.json()) as StoredCase;
        if (updated.id !== record.id) throw new Error('Unexpected case response');
        setRecord(updated);
      }
      const outcome = classifySingleAnswer(questionIndex, selected);
      setNotice(t.savedAnswerSaved);
      if (outcome === 'pass') {
        if (questionIndex === 4) setReviewing(true);
        else {
          setQuestionIndex(questionIndex + 1);
          setSelected(updated.scope_answers[questionIndex + 1] ?? null);
        }
      }
    } catch {
      setError(t.savedAnswerError);
    } finally {
      setSaving(false);
    }
  }

  async function deleteCase() {
    if (!record || deleting || !window.confirm(t.savedDeleteConfirm)) return;
    setDeleting(true);
    setError('');
    try {
      const response = await fetch('/api/cases/' + caseId, {
        method: 'DELETE',
        credentials: 'same-origin',
      });
      if (response.status !== 204) throw new Error('Delete failed');
      router.push('/cases/saved');
      router.refresh();
    } catch {
      setError(t.savedDeleteError);
      setDeleting(false);
    }
  }

  if (!configured || !signedIn) {
    return <main className="subpage-background" id="main-content">
      <div className="container account-shell">
        <h1 className="subpage-title">{t.savedWorkspaceTitle}</h1>
        <p>{!configured ? t.savedBackendUnavailable : t.savedSignIn}</p>
        <a className="button button-primary" href="/auth/login">{t.accountLogin}</a>
      </div>
    </main>;
  }

  return <main className="workspace-page" id="main-content" tabIndex={-1}>
    <div className="container workspace-head">
      <div className="workspace-title-group">
        <span className="tiny-eyebrow">{t.demo}</span>
        <h1>{t.savedWorkspaceTitle}</h1>
        <p>{t.savedWorkspaceIntro}</p>
      </div>
      <Link className="exit-link" href="/cases/saved">{t.savedBackToCases}</Link>
    </div>
    <div className="container workspace-grid" style={{ marginTop: 28 }}>
      <section className="work-panel" aria-busy={saving || loading}>
        {loading && <div className="panel-intro" role="status">{t.savedLoading}</div>}
        {!loading && !record && <div className="panel-intro">
          <h2>{t.savedUnavailableTitle}</h2>
          <p>{t.savedUnavailableBody}</p>
          <button type="button" className="button button-outline" onClick={() => void load()}>{t.savedRetry}</button>
        </div>}
        {!loading && record && reviewing && <>
          <div className="panel-intro">
            <span className="tiny-eyebrow">{t.savedDemoReview}</span>
            <h2>{t.savedReviewTitle}</h2>
            <p>{t.savedReviewBody}</p>
          </div>
          <div className="panel-rule" />
          <div className="scope-content">
            <ol className="side-checklist">
              {t.questions.map((question, index) => <li key={question}>
                <button type="button" className="inline-link" onClick={() => openQuestion(index)}>
                  {question} — {record.scope_answers[index] === 'yes' ? t.answerYes
                    : record.scope_answers[index] === 'no' ? t.answerNo : t.answerUnsure}
                </button>
              </li>)}
            </ol>
            <div className="message-box notice" role="status">{t.savedNotEligibility}</div>
          </div>
          <div className="panel-bottom">
            <button type="button" className="button button-outline" onClick={() => openQuestion(4)}>{t.savedEditAnswers}</button>
            <Link href="/cases/saved" className="button button-primary">{t.savedBackToCases}</Link>
          </div>
        </>}
        {!loading && record && !reviewing && <>
          <div className="panel-intro">
            <span className="tiny-eyebrow">{t.scopeEyebrow}</span>
            <h2>{t.scopeTitle}</h2>
            <p>{t.savedProgress} {record.scope_answers.length} / 5 — {t.savedDraft}: {record.status}</p>
          </div>
          <div className="panel-rule" />
          <div className="scope-content">
            <span className="question-count">{t.questionLabel} {questionIndex + 1} / 5</span>
            <h3>{t.questions[questionIndex]}</h3>
            <div className="answer-grid" role="group" aria-label={t.questions[questionIndex]}>
              {ANSWERS.map((option) =>
                <button type="button" key={option}
                  className={`answer-option ${selected === option ? 'selected' : ''}`}
                  aria-pressed={selected === option} disabled={saving || deleting}
                  onClick={() => { setSelected(option); setError(''); setNotice(''); }}>
                  <span className="answer-radio" />
                  {option === 'yes' ? t.answerYes : option === 'no' ? t.answerNo : t.answerUnsure}
                </button>)}
            </div>
            {selected && classifySingleAnswer(questionIndex, selected) === 'unsupported'
              && <div role="status" className="message-box warning"><div><strong>{t.blockedTitle}</strong><p>{t.blockedBody}</p></div></div>}
            {selected === 'unsure'
              && <div role="status" className="message-box notice"><div><strong>{t.unsureTitle}</strong><p>{t.unsureBody}</p></div></div>}
            <details className="why-disclosure"><summary>{t.questionWhy}</summary><p>{t.questionWhyBody}</p></details>
          </div>
          <div className="panel-bottom">
            <button type="button" className="button button-outline" disabled={saving || deleting}
              onClick={() => questionIndex === 0 ? router.push('/cases/saved') : openQuestion(questionIndex - 1)}>
              {t.back}
            </button>
            <button type="button" className="button button-primary" disabled={!selected || saving || deleting}
              onClick={() => void saveAnswer()}>
              {saving ? t.savedSavingAnswer : t.savedSaveContinue}
            </button>
          </div>
        </>}
        {notice && <p className="container" role="status" style={{ padding: '12px 24px' }}>{notice}</p>}
        {error && <p className="error-text" role="alert" style={{ padding: '12px 24px' }}>{error}</p>}
      </section>
      <aside className="case-sidebar" aria-label={t.sidebarTasks}>
        <section className="side-panel">
          <h2>{t.savedCaseDetails}</h2>
          <p>{t.savedSyntheticOnly}</p>
          {record && <>
            <div className="fact-row"><span>{t.savedCaseCode}</span><strong>{record.id.slice(0, 8)}</strong></div>
            <div className="fact-row"><span>{t.savedDraft}</span><strong>{record.status}</strong></div>
            <div className="fact-row"><span>{t.savedProgress}</span><strong>{record.scope_answers.length} / 5</strong></div>
            {assistantEnabled && <Link
              href={'/cases/' + encodeURIComponent(caseId) + '/assistant'}
              className="button button-outline" style={{ marginTop: 18, display: 'inline-flex' }}>
              {locale === 'it' ? 'Anteprima assistente con fonti' : 'Evidence assistant preview'}
            </Link>}
            <button type="button" className="button button-outline" style={{ marginTop: 22 }}
              disabled={saving || deleting} onClick={() => void deleteCase()}>
              {deleting ? t.savedDeleting : t.savedDelete}
            </button>
          </>}
        </section>
        <p className="side-footnote">{t.accountDemoPrivacy}</p>
      </aside>
    </div>
  </main>;
}
