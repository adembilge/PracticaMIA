'use client';

import Link from 'next/link';
import { useDemo } from '@/components/DemoProvider';
import { Icon } from '@/components/Icon';

export function CaseSidebar() {
  const { t, data } = useDemo();
  return <aside className="case-sidebar" aria-label={t.sidebarFacts}>
    <section className="side-panel">
      <div className="side-heading"><span className="side-icon"><Icon name="home" size={17}/></span><h2>{t.sidebarFacts}</h2></div>
      <div className="fact-list">
        <div className="fact-row"><span>{t.prevAddress}</span><strong>{data.previousAddress || t.sidebarUnknown}</strong></div>
        <div className="fact-row"><span>{t.newAddress}</span><strong>{data.newAddress || t.sidebarUnknown}</strong></div>
        <div className="fact-row"><span>{t.moveDate}</span><strong>{data.movedOn || t.sidebarUnknown}</strong></div>
      </div>
      <span className={`tiny-status ${data.factsConfirmed ? 'good' : ''}`}><Icon name={data.factsConfirmed ? 'check' : 'clock'} size={13}/>{data.factsConfirmed ? t.tagConfirmed : t.tagPending}</span>
    </section>
    <section className="side-panel">
      <div className="side-heading"><span className="side-icon"><Icon name="list" size={17}/></span><h2>{t.sidebarTasks}</h2></div>
      <ul className="side-checklist">
        <li><span className={`side-check ${data.phase !== 'scope' ? 'done' : ''}`}><Icon name={data.phase !== 'scope' ? 'check' : 'clock'} size={13}/></span>{t.statusScope}</li>
        <li><span className={`side-check ${data.factsConfirmed ? 'done' : ''}`}><Icon name={data.factsConfirmed ? 'check' : 'clock'} size={13}/></span>{t.statusFacts}</li>
        <li><span className="side-check"><Icon name="clock" size={13}/></span>{t.statusDocs}</li>
      </ul>
    </section>
    <section className="side-footnote"><Icon name="info" size={16}/><span>{t.fakeNotice}</span></section>
  </aside>;
}
