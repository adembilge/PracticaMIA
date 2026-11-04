'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useDemo } from '@/components/DemoProvider';
import { Icon } from '@/components/Icon';

const MUNICIPAL_GUIDE = 'https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza';

export default function ReviewPage() {
  const router = useRouter();
  const { t, data, setPhase } = useDemo();
  const readyForDemoReview = data.factsConfirmed && data.phase === 'checklist';
  return <main id="main-content" tabIndex={-1} className="subpage-background"><div className="container review-shell">
    <Link href="/cases/demo" className="back-link"><Icon name="arrowLeft" size={17}/>{t.reviewBack}</Link>
    <div className="review-header"><span className="tiny-eyebrow">{t.reviewEyebrow}</span><h1 className="subpage-title">{t.reviewTitle}</h1><p className="lead">{t.reviewLead}</p></div>
    {!readyForDemoReview ? <div className="message-box notice"><Icon name="info" size={21}/><div><p>{t.emptyReview}</p><Link className="source-link" href="/cases/demo">{t.reviewBack}<Icon name="arrowRight" size={14}/></Link></div></div> : <div className="review-grid">
      <section className="review-card"><div className="review-card-header"><div className="side-icon"><Icon name="file" size={19}/></div><h2>{t.summaryTitle}</h2><span className="tiny-status good"><Icon name="check" size={13}/>{t.tagConfirmed}</span></div><dl className="review-facts"><div><dt>{t.prevAddress}</dt><dd>{data.previousAddress}</dd></div><div><dt>{t.newAddress}</dt><dd>{data.newAddress}</dd></div><div><dt>{t.moveDate}</dt><dd>{data.movedOn}</dd></div><div><dt>{t.summaryScope}</dt><dd>{t.summaryScopeValue}</dd></div></dl><button type="button" className="button button-outline" onClick={() => { setPhase('intake'); router.push('/cases/demo'); }}><Icon name="edit" size={16}/>{t.reviewEdit}</button></section>
      <section className="review-card"><div className="review-card-header"><div className="side-icon"><Icon name="list" size={19}/></div><h2>{t.summaryNext}</h2></div><ol className="review-next"><li>{t.summaryNext1}</li><li>{t.summaryNext2}</li><li>{t.summaryNext3}</li></ol><a className="source-link" href={MUNICIPAL_GUIDE} target="_blank" rel="noopener noreferrer"><Icon name="external" size={16}/>{t.officialLink}</a></section>
    </div>}
    <div className="message-box warning review-warning" role="note"><Icon name="alert" size={20}/><div>{t.submissionAlert}</div></div>
    <div className="review-actions"><Link href="/cases/demo" className="button button-outline"><Icon name="arrowLeft" size={17}/>{t.revisit}</Link></div>
  </div></main>;
}
