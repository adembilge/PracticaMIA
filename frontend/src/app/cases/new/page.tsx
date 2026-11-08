'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { type FormEvent } from 'react';
import { Icon } from '@/components/Icon';
import { useDemo } from '@/components/DemoProvider';

export default function NewCasePage() {
  const router = useRouter();
  const { t, data, setGoal, reset } = useDemo();
  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!data.goal.trim()) return;
    router.push('/cases/demo');
  }
  return <main id="main-content" tabIndex={-1} className="subpage-background"><div className="container new-case-shell">
    <Link href="/" className="back-link"><Icon name="arrowLeft" size={16}/>{t.back}</Link>
    <div className="new-grid">
      <section className="new-main">
        <span className="tiny-eyebrow">{t.newKicker}</span>
        <h1 className="subpage-title">{t.newTitle}</h1>
        <p className="lead">{t.newLead}</p>
        <p><Link href="/cases/saved" className="inline-link">Use a saved, resumable case instead (sign-in required)</Link></p>
        <p><Link href="/demo/synthetic" className="inline-link">See the complete fictional document-to-handoff walkthrough</Link></p>
        <form onSubmit={submit} className="new-form">
          <label htmlFor="case-goal" className="field-label">{t.newLabel}</label>
          <textarea id="case-goal" className="input input-textarea" maxLength={500} value={data.goal} onChange={(e) => setGoal(e.target.value)} placeholder={t.newPlaceholder} rows={5} required />
          <div className="form-meta"><button type="button" className="inline-link" onClick={() => setGoal(t.newPlaceholder)}>{t.newExample}</button><span>{data.goal.length}/500</span></div>
          <button type="submit" className="button button-primary button-wide" disabled={!data.goal.trim()}>{t.newContinue}<Icon name="arrowRight" size={18}/></button>
        </form>
      </section>
      <aside className="new-aside">
        <div className="aside-icon"><Icon name="home" size={24}/></div>
        <h2>{t.newNoteTitle}</h2>
        <p>{t.newNote}</p>
        <div className="aside-rule" />
        <div className="privacy-inline"><Icon name="lock" size={18}/><p>{t.newPrivacy}</p></div>
        <button type="button" className="small-reset" onClick={reset}>{t.restart}</button>
      </aside>
    </div>
  </div></main>;
}
