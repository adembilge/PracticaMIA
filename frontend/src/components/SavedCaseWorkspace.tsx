'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { type Answer, useDemo } from '@/components/DemoProvider';
import { classifySingleAnswer } from '@/lib/flow.js';
import { SavedCaseAIGuide } from '@/components/SavedCaseAIGuide';
import { ReviewedSourcesPanel } from '@/components/ReviewedSourcesPanel';
import { CaseIntakePanel } from '@/components/CaseIntakePanel';
import { CaseJourneyPanel } from '@/components/CaseJourneyPanel';
import { firstUnresolvedQuestion, isCaseId, nextScopeAnswers } from '@/lib/case-scope.js';

type StoredCase = {
  id: string;
  procedure: string;
  status: string;
  scope_answers: Answer[];
  created_at: string;
  updated_at: string;
};

type Props = { caseId: string; configured: boolean; signedIn: boolean; assistantEnabled: boolean; preparationEnabled: boolean; liveAIEnabled: boolean; privateDocumentsEnabled: boolean; fictionalDocumentsEnabled?: boolean };
const ANSWERS: Answer[] = ['yes', 'no', 'unsure'];

export function SavedCaseWorkspace({ caseId, configured, signedIn, assistantEnabled, preparationEnabled, liveAIEnabled, privateDocumentsEnabled, fictionalDocumentsEnabled = false }: Props) {
  const router = useRouter();
  const { t, locale } = useDemo();
  const [record, setRecord] = useState<StoredCase | null>(null);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [scopeDirection, setScopeDirection] = useState('forward');
  const questionHeading = useRef<HTMLHeadingElement>(null);
  const [expired, setExpired] = useState(false);
  const [selected, setSelected] = useState<Answer | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<'load' | 'save' | 'delete' | null>(null);
  const [notice, setNotice] = useState('');
  const [journeyRevision, setJourneyRevision] = useState(0);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/cases/' + caseId, { cache: 'no-store', signal });
      if (response.status === 401) { if (!signal?.aborted) setExpired(true); return; }
      if (!response.ok) throw new Error('Case unavailable');
      const saved = (await response.json()) as StoredCase;
      if (saved.id !== caseId || !Array.isArray(saved.scope_answers)) throw new Error('Invalid response');
      if (signal?.aborted) return;
      setExpired(false);
      const index = firstUnresolvedQuestion(saved.scope_answers);
      setRecord(saved);
      setQuestionIndex(index);
      setSelected(saved.scope_answers[index] ?? null);
      setReviewing(saved.status === 'provisionally_in_scope' && saved.scope_answers.length === 5);
    } catch {
      if (!signal?.aborted) setError('load');
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [caseId]);

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
    setScopeDirection(index < questionIndex || reviewing ? 'back' : 'forward');
    setQuestionIndex(index);
    setSelected(data.scope_answers[index] ?? null);
    setReviewing(false);
    setError(null);
    setNotice('');
    requestAnimationFrame(() => questionHeading.current?.focus());
  }

  async function saveAnswer() {
    if (!record || !selected || saving || expired) return;
    setSaving(true);
    setError(null);
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
        if (response.status === 401) { setExpired(true); return; }
        if (!response.ok) throw new Error('Save failed');
        updated = (await response.json()) as StoredCase;
        if (updated.id !== record.id) throw new Error('Unexpected case response');
        setRecord(updated);
        setJourneyRevision(n => n + 1);
      }
      const outcome = classifySingleAnswer(questionIndex, selected);
      setNotice(t.savedAnswerSaved);
      if (outcome === 'pass') {
        if (questionIndex === 4) {
          setReviewing(true);
          if (window.location.hash === '#case-scope') {
            window.history.pushState(null, '', '#case-intake');
            window.dispatchEvent(new Event('hashchange'));
          }
        } else {
          setScopeDirection('forward');
          setQuestionIndex(questionIndex + 1);
          setSelected(updated.scope_answers[questionIndex + 1] ?? null);
          requestAnimationFrame(() => questionHeading.current?.focus());
        }
      }
    } catch {
      setError('save');
    } finally {
      setSaving(false);
    }
  }

  async function deleteCase() {
    if (!record || deleting || expired || !window.confirm(t.savedDeleteConfirm)) return;
    setDeleting(true);
    setError(null);
    try {
      const response = await fetch('/api/cases/' + caseId, {
        method: 'DELETE',
        credentials: 'same-origin',
      });
      if (response.status === 401) { setExpired(true);setDeleting(false);return; }
      if (response.status !== 204) throw new Error('Delete failed');
      router.push('/cases/saved');
      router.refresh();
    } catch {
      setError('delete');
      setDeleting(false);
    }
  }

  if (!configured || !signedIn) {
    return <main className="subpage-background" id="main-content">
      <div className="container account-shell">
        <h1 className="subpage-title">{t.savedWorkspaceTitle}</h1>
        <p>{!configured ? t.savedBackendUnavailable : t.savedSignIn}</p>
        {configured && <a className="button button-primary" href={'/auth/login?returnTo=' + encodeURIComponent('/cases/' + caseId)}>{t.accountLogin}</a>}
      </div>
    </main>;
  }

  const scopeComplete = record?.status === 'provisionally_in_scope' && record.scope_answers.length === 5;
  const login = '/auth/login?returnTo=' + encodeURIComponent('/cases/' + caseId);
  return <main className="case-page" id="main-content" tabIndex={-1}>
    <div className="container">
      <header className="case-header">
        <div><p className="editorial-label">{locale === 'it' ? 'Milano · Pratica di esempio' : 'Milano · Example case'}{record && ' / ' + record.id.slice(0, 8)}</p>
          <h1>{t.savedWorkspaceTitle}</h1></div>
        <Link className="editorial-text-link" href="/cases/saved">← {t.savedBackToCases}</Link>
      </header>
      {expired && <div className="message-box warning" role="alert"><div>
        <strong>{locale === 'it' ? 'La sessione è scaduta' : 'Your session has expired'}</strong>
        <p><a className="inline-link" href={login}>{locale === 'it' ? 'Accedi di nuovo' : 'Sign in again'}</a></p>
      </div></div>}
      {loading && <p className="editorial-pending" role="status">{t.savedLoading}</p>}
      {!loading && !record && !expired && <section className="case-state" role="alert">
        <h2>{t.savedUnavailableTitle}</h2><p>{t.savedUnavailableBody}</p>
        <button type="button" className="button button-outline" onClick={() => void load()}>{t.savedRetry}</button>
      </section>}
      {record && <CaseJourneyPanel caseId={caseId} refreshKey={journeyRevision}
        scopeComplete={Boolean(scopeComplete)} privateDocumentsEnabled={privateDocumentsEnabled}
        fictionalDocumentsEnabled={fictionalDocumentsEnabled} preparationEnabled={preparationEnabled} assistantEnabled={assistantEnabled}
        sources={<ReviewedSourcesPanel locale={locale}/>}
        guidance={liveAIEnabled ? <SavedCaseAIGuide
          key={record.id + ':' + record.scope_answers.join(',')} caseId={caseId}
          snapshot={{status: record.status, scope_answers: record.scope_answers}}/> : null}
        scope={reviewing ? <div className="scope-review" id="case-scope">
          <h3>{t.savedReviewTitle}</h3><p>{t.savedReviewBody}</p>
          <ol>{t.questions.map((question, index) => <li key={question}>
            <button type="button" className="scope-review-row" onClick={() => openQuestion(index)}>
              <span>{question}</span><strong>{record.scope_answers[index] === 'yes' ? t.answerYes :
                record.scope_answers[index] === 'no' ? t.answerNo : t.answerUnsure}</strong>
            </button>
          </li>)}</ol>
          <p className="case-state">{t.savedNotEligibility}</p>
        </div> : <div className="scope-question" id="case-scope" aria-busy={saving}>
          <div className="scope-motion" key={questionIndex} data-direction={scopeDirection}>
            <p className="editorial-label question-count">{t.questionLabel} {questionIndex + 1} / 5</p>
            <h3 ref={questionHeading} tabIndex={-1}>{t.questions[questionIndex]}</h3>
            {questionIndex === 0 && <p>{t.previousRegistrationHelp}</p>}
            <div className="answer-grid" role="group" aria-label={t.questions[questionIndex]}>
              {ANSWERS.map(option => <button type="button" key={option}
                className={'answer-option' + (selected === option ? ' selected' : '')}
                aria-pressed={selected === option} disabled={saving || deleting || expired}
                onClick={() => { setSelected(option);setError(null);setNotice(''); }}>
                <span className="answer-radio"/>
                {option === 'yes' ? t.answerYes : option === 'no' ? t.answerNo : t.answerUnsure}
              </button>)}
            </div>
            {selected && classifySingleAnswer(questionIndex, selected) === 'unsupported' &&
              <div role="status" className="message-box warning"><div><strong>{t.blockedTitle}</strong><p>{t.blockedBody}</p></div></div>}
            {selected === 'unsure' && <div role="status" className="message-box notice"><div><strong>{t.unsureTitle}</strong><p>{t.unsureBody}</p></div></div>}
            <details className="why-disclosure"><summary>{t.questionWhy}</summary><p>{t.questionWhyBody}</p></details>
          </div>
          <div className="case-actions">
            <button type="button" className="button button-outline" disabled={saving || deleting || expired}
              onClick={() => questionIndex === 0 ? router.push('/cases/saved') : openQuestion(questionIndex - 1)}>{t.back}</button>
            <button type="button" className="button button-primary" disabled={!selected || saving || deleting || expired}
              onClick={() => void saveAnswer()}>{saving ? t.savedSavingAnswer : t.savedSaveContinue}</button>
          </div>
          {error === 'save' && <div className="message-box warning" role="alert"><div><p>{t.savedAnswerError}</p>
            <button type="button" className="inline-link" onClick={() => void saveAnswer()}>{t.savedRetry}</button>
          </div></div>}
          {notice && <p className="case-confirmation" role="status">{notice}</p>}
        </div>}
        intake={<CaseIntakePanel caseId={caseId} onChanged={() => setJourneyRevision(n => n + 1)}/>}
      />}
      {record && <details className="case-settings case-more">
        <summary>{locale === 'it' ? 'Gestisci la pratica' : 'Manage this case'}</summary><p>{t.savedSyntheticOnly}</p>
        <div className="case-actions">
          <button type="button" className="button button-outline" disabled={saving || deleting || expired}
            onClick={() => void deleteCase()}>{deleting ? t.savedDeleting : t.savedDelete}</button>
        </div>
        {error === 'delete' && <p className="error-text" role="alert">{t.savedDeleteError}</p>}
      </details>}
    </div>
  </main>;
}
