'use client';

import Link from 'next/link';
import { Icon } from '@/components/Icon';
import { useDemo } from '@/components/DemoProvider';

export default function WelcomePage() {
  const { t } = useDemo();
  return <main id="main-content" tabIndex={-1}>
    <section className="home-hero container">
      <div className="hero-copy">
        <div className="eyebrow"><span className="eyebrow-line" />{t.homeKicker}</div>
        <h1>{t.homeTitle1}<br/><em>{t.homeTitle2}</em></h1>
        <p className="lead hero-lead">{t.homeLead}</p>
        <div className="hero-actions">
          <Link href="/cases/saved" className="button button-primary">{t.homePrimary}<Icon name="arrowRight" size={18}/></Link>
          <Link href="/#how-it-works" className="button button-text">{t.homeSecondary}<Icon name="arrowRight" size={16}/></Link>
        </div>
        <p className="hero-smallprint"><Icon name="shield" size={16}/>{t.independent}</p>
        <p className="hero-smallprint"><Link href="/demo/synthetic">Try the complete fictional workflow (no login required)</Link></p>
      </div>
      <div className="hero-visual" aria-label={t.visualTitle}>
        <div className="visual-grid-decor"/>
        <div className="sample-card">
          <div className="sample-card-top"><span className="tiny-eyebrow">{t.visualEyebrow}</span><span className="status-dot"/></div>
          <h2>{t.visualTitle}</h2>
          <div className="sample-status"><span className="sample-pulse"/>{t.visualStatus}</div>
          <div className="sample-progress"><span/></div>
          <div className="sample-row"><span className="sample-number complete">01</span><span>{t.visualStep}</span><Icon name="check" size={17}/></div>
          <div className="sample-row"><span className="sample-number current">02</span><span>{t.visualStep2}</span><span className="mini-bars"><i/><i/><i/></span></div>
          <div className="sample-row dim"><span className="sample-number">03</span><span>{t.visualStep3}</span><span className="empty-circle"/></div>
          <div className="sample-footer"><Icon name="lock" size={15}/> {t.fakeNotice}</div>
        </div>
        <div className="floating-note"><span className="floating-icon"><Icon name="file" size={20}/></span><span>Comune di Milano<br/><strong>Official guidance linked</strong></span></div>
      </div>
    </section>
    <section id="how-it-works" className="how-section">
      <div className="container">
        <span className="tiny-eyebrow">{t.howEyebrow}</span><h2>{t.howTitle}</h2>
        <div className="feature-grid">
          <article className="feature"><span className="feature-number">01</span><div className="feature-icon"><Icon name="edit" size={25}/></div><h3>{t.howA}</h3><p>{t.howAD}</p></article>
          <article className="feature"><span className="feature-number">02</span><div className="feature-icon"><Icon name="list" size={25}/></div><h3>{t.howB}</h3><p>{t.howBD}</p></article>
          <article className="feature"><span className="feature-number">03</span><div className="feature-icon"><Icon name="shield" size={25}/></div><h3>{t.howC}</h3><p>{t.howCD}</p></article>
        </div>
        <div className="how-footer"><Icon name="info" size={18}/><span>{t.homeBottom}</span></div>
      </div>
    </section>
    <footer className="site-footer container"><span>© PracticaMIA</span><span>{t.footer}</span></footer>
  </main>;
}
