'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { type Answer, type Field, useDemo } from '@/components/DemoProvider';
import { CaseSidebar } from '@/components/CaseSidebar';
import { Icon } from '@/components/Icon';
import { classifySingleAnswer, validateIntake, sameAddressWarning } from '@/lib/flow.js';

const OFFICIAL_GUIDANCE = 'https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza';

export function CaseWorkspace() {
  const router = useRouter();
  const { t, data, answer, setQuestionIndex, setPhase, updateField, confirmFacts, reset } = useDemo();
  const stepHeadingRef = useRef<HTMLHeadingElement>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const errors = useMemo(() => validateIntake(data), [data]);
  const duplicated = sameAddressWarning(data);
  const scopeAnswer = data.answers[data.questionIndex];
  const answerOutcome = scopeAnswer ? classifySingleAnswer(data.questionIndex, scopeAnswer) : 'none';
  const step = data.phase === 'scope' ? 1 : data.phase === 'intake' ? 2 : 3;

  // Move keyboard focus when the wizard displays a new question or phase.
  useEffect(() => { stepHeadingRef.current?.focus(); }, [data.phase, data.questionIndex]);

  function goNextScope() {
    if (answerOutcome !== 'pass') return;
    if (data.questionIndex === 4) setPhase('intake');
    else setQuestionIndex(data.questionIndex + 1);
  }
  function submitIntake(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setAttempted(true);
    if (Object.keys(errors).length || duplicated || !acknowledged) return;
    confirmFacts();
  }
  function setInput(field: Field, value: string) { updateField(field, value); setAttempted(false); setAcknowledged(false); }
  function beginAgain() { reset(); router.push('/cases/new'); }

  return <main id="main-content" tabIndex={-1} className="workspace-page">
    <div className="container workspace-head">
      <div className="workspace-title-group"><span className="tiny-eyebrow">{t.demo}</span><h1>{t.workspaceTitle}</h1><p>{t.workspaceSub}</p></div>
      <Link className="exit-link" href="/"><Icon name="x" size={16}/>{t.exit}</Link>
    </div>
    <div className="container progress-strip" role="list" aria-label="Demo progress">
      {[t.stepScope, t.stepIntake, t.stepChecklist].map((title, i) => <div className={`progress-step ${step === i + 1 ? 'active' : ''} ${step > i + 1 ? 'complete' : ''}`} key={title} role="listitem" aria-current={step === i + 1 ? "step" : undefined}>
        <span className="progress-bullet">{step > i + 1 ? <Icon name="check" size={13}/> : i + 1}</span><span>{title}</span>
      </div>)}
    </div>
    <div className="container workspace-grid">
      <section className="work-panel">
        {data.phase === 'scope' && <>
          <div className="panel-intro"><span className="tiny-eyebrow">{t.scopeEyebrow}</span><h2>{t.scopeTitle}</h2><p>{t.scopeLead}</p></div>
          <div className="panel-rule" />
          <div className="scope-content">
            <span className="question-count">{t.questionLabel} {data.questionIndex + 1} / 5</span>
            <h3 ref={stepHeadingRef} tabIndex={-1}>{t.questions[data.questionIndex]}</h3>
            <div className="answer-grid" role="group" aria-label={t.questions[data.questionIndex]}>
              {(['yes', 'no', 'unsure'] as Answer[]).map((option) => <button type="button" className={`answer-option ${scopeAnswer === option ? 'selected' : ''}`} key={option} aria-pressed={scopeAnswer === option} onClick={() => answer(data.questionIndex, option)}><span className="answer-radio"/>{option === 'yes' ? t.answerYes : option === 'no' ? t.answerNo : t.answerUnsure}</button>)}
            </div>
            {answerOutcome === 'unsupported' && <div className="message-box warning" role="status"><Icon name="alert" size={20}/><div><strong>{t.blockedTitle}</strong><p>{t.blockedBody}</p></div></div>}
            {answerOutcome === 'needs_information' && <div className="message-box notice" role="status"><Icon name="info" size={20}/><div><strong>{t.unsureTitle}</strong><p>{t.unsureBody}</p></div></div>}
            <details className="why-disclosure"><summary>{t.questionWhy}<Icon name="chevronDown" size={16}/></summary><p>{t.questionWhyBody}</p></details>
          </div>
          <div className="panel-bottom"><button type="button" className="button button-outline" onClick={() => data.questionIndex === 0 ? router.push('/cases/new') : setQuestionIndex(data.questionIndex - 1)}><Icon name="arrowLeft" size={17}/>{t.back}</button><button type="button" className="button button-primary" disabled={answerOutcome !== 'pass'} onClick={goNextScope}>{t.continue}<Icon name="arrowRight" size={17}/></button></div>
        </>}
        {data.phase === 'intake' && <>
          <div className="panel-intro"><span className="tiny-eyebrow">{t.intakeEyebrow}</span><h2 ref={stepHeadingRef} tabIndex={-1}>{t.intakeTitle}</h2><p>{t.intakeLead}</p></div>
          <div className="panel-rule" />
          <form onSubmit={submitIntake} noValidate className="intake-form">
            {([['previousAddress', t.prevAddress, t.prevAddressPlaceholder], ['newAddress', t.newAddress, t.newAddressPlaceholder]] as const).map(([field, label, placeholder]) => <div className="field-block" key={field}><label className="field-label" htmlFor={field}>{label}</label><input className={`input ${attempted && errors[field] ? 'has-error' : ''}`} id={field} autoComplete="off" value={data[field]} onChange={(e) => setInput(field, e.target.value)} placeholder={placeholder} aria-invalid={Boolean(attempted && errors[field])} aria-describedby={attempted && errors[field] ? `${field}-error` : undefined}/>{attempted && errors[field] && <small id={`${field}-error`} className="error-text" role="alert">{t.missing}</small>}</div>)}
            <div className="field-block"><label className="field-label" htmlFor="movedOn">{t.moveDate}</label><input className={`input date-input ${attempted && errors.movedOn ? 'has-error' : ''}`} type="date" id="movedOn" value={data.movedOn} onChange={(e) => setInput('movedOn', e.target.value)} aria-invalid={Boolean(attempted && errors.movedOn)} aria-describedby={attempted && errors.movedOn ? "movedOn-help movedOn-error" : "movedOn-help"}/><small id="movedOn-help" className="field-help">{t.dateNote}</small>{attempted && errors.movedOn && <small id="movedOn-error" className="error-text" role="alert">{errors.movedOn === 'invalid' ? t.badDate : t.missing}</small>}</div>
            {duplicated && <div className="message-box warning" role="alert"><Icon name="alert" size={19}/><div>{t.sameAddress}</div></div>}
            <label className="consent-row"><input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} aria-describedby={attempted && !acknowledged ? "consent-error" : undefined}/><span>{t.acknowledge}</span></label>
            {attempted && !acknowledged && <span id="consent-error" className="error-text" role="alert">{t.acknowledge}</span>}
            <div className="panel-bottom form-bottom"><button type="button" className="button button-outline" onClick={() => setQuestionIndex(4)}><Icon name="arrowLeft" size={17}/>{t.back}</button><button type="submit" className="button button-primary">{t.confirmButton}<Icon name="arrowRight" size={17}/></button></div>
          </form>
        </>}
        {data.phase === 'checklist' && <>
          <div className="panel-intro"><span className="tiny-eyebrow">{t.checklistEyebrow}</span><h2 ref={stepHeadingRef} tabIndex={-1}>{t.checklistTitle}</h2><p>{t.checklistLead}</p></div>
          <div className="panel-rule" />
          <div className="checklist-list">
            <ChecklistItem done number="01" title={t.checklistItem1} desc={t.checklistItem1D} tag={t.statusDone}/>
            <ChecklistItem done={data.factsConfirmed} number="02" title={t.checklistItem2} desc={t.checklistItem2D} tag={data.factsConfirmed ? t.statusDone : t.statusPending}/>
            <ChecklistItem number="03" title={t.checklistItem3} desc={t.checklistItem3D} tag={t.statusPending}/>
            <ChecklistItem number="04" title={t.checklistItem4} desc={t.checklistItem4D} tag={t.sources} link={OFFICIAL_GUIDANCE} linkText={t.sourceName}/>
          </div>
          <div className="message-box notice checklist-notice"><Icon name="info" size={18}/><div>{t.fakeNotice}</div></div>
          <div className="panel-bottom"><button type="button" className="button button-outline" onClick={() => setPhase('intake')}><Icon name="edit" size={16}/>{t.editFacts}</button><Link href="/cases/demo/review" className="button button-primary">{t.reviewButton}<Icon name="arrowRight" size={17}/></Link></div>
        </>}
      </section>
      <CaseSidebar />
    </div>
    <div className="container below-workspace"><button type="button" className="small-reset" onClick={beginAgain}>{t.restart}</button></div>
  </main>;
}

function ChecklistItem({ number, title, desc, tag, done = false, link, linkText }: { number: string; title: string; desc: string; tag: string; done?: boolean; link?: string; linkText?: string }) {
  return <div className="checklist-item"><span className={`checklist-number ${done ? 'done' : ''}`}>{done ? <Icon name="check" size={16}/> : number}</span><div className="checklist-detail"><div className="checklist-top"><h3>{title}</h3><span className={`checklist-tag ${done ? 'done' : ''}`}>{tag}</span></div><p>{desc}</p>{link && <a href={link} className="source-link" target="_blank" rel="noopener noreferrer"><Icon name="external" size={15}/>{linkText}</a>}</div></div>;
}
