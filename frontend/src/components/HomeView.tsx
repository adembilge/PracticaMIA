'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Icon } from '@/components/Icon';
import { useDemo } from '@/components/DemoProvider';
import { isCaseId } from '@/lib/case-scope.js';

const copy = {
  en: {
    region: 'Milano · Change of residence', title: 'Moving to', accent: 'a new address?',
    description: 'Prepare your Milan residence change, check your documents and put together a draft before you file.',
    start: 'Prepare my case', resume: 'Continue my case', cases: 'Open my cases', demo: 'Try a fictional case',
    specimen: 'Example case', specimenTitle: 'Change of residence', caption: 'Fictional data for this preview',
    tabs: ['Requirements', 'Document check', 'Summary'],
    requirements: ['Residence details', 'Housing information'], selected: 'Selected requirement',
    explanations: ['Review the previous and new address details for this example.', 'Compare the housing entry with the sample document.'],
    source: 'Example case details', evidence: 'Check the sample document',
    document: 'Sample housing document', page: 'Page 1', field: 'Move-in date',
    caseValue: 'In the case', docValue: 'In the document', conflict: 'Dates differ',
    summary: 'Preparation draft', blocked: 'One field to review', official: 'Official filing', userOnly: 'Completed separately on ANPR',
    backToCheck: 'See the field to review', how: 'How preparation works',
  },
  it: {
    region: 'Milano · Cambio di residenza', title: 'Ti trasferisci', accent: 'a un nuovo indirizzo?',
    description: 'Prepara il cambio di residenza a Milano, controlla i documenti e organizza una bozza prima dell’invio.',
    start: 'Prepara la mia pratica', resume: 'Continua la pratica', cases: 'Apri le mie pratiche', demo: 'Prova un caso fittizio',
    specimen: 'Pratica di esempio', specimenTitle: 'Cambio di residenza', caption: 'Anteprima con dati fittizi',
    tabs: ['Requisiti', 'Controllo documenti', 'Riepilogo'],
    requirements: ['Dati di residenza', 'Dati dell’alloggio'], selected: 'Requisito selezionato',
    explanations: ['Controlla i dati del vecchio e del nuovo indirizzo di esempio.', 'Confronta il dato sull’alloggio con il documento di esempio.'],
    source: 'Dati della pratica di esempio', evidence: 'Controlla il documento di esempio',
    document: 'Documento di esempio sull’alloggio', page: 'Pagina 1', field: 'Data del trasferimento',
    caseValue: 'Nella pratica', docValue: 'Nel documento', conflict: 'Le date non coincidono',
    summary: 'Bozza di preparazione', blocked: 'Un campo da esaminare', official: 'Invio ufficiale', userOnly: 'Da effettuare separatamente su ANPR',
    backToCheck: 'Mostra il campo da esaminare', how: 'Come funziona la preparazione',
  },
} as const;

export function HomeView({ signedIn, canList, syntheticDemo }: { signedIn: boolean; canList: boolean; syntheticDemo: boolean }) {
  const { locale, t } = useDemo();
  const c = copy[locale];
  const [cases, setCases] = useState<string[] | null>(null);
  const [view, setView] = useState(0);
  const [requirement, setRequirement] = useState(0);

  useEffect(() => {
    if (!canList) return;
    const controller = new AbortController();
    async function loadCases() {
      try {
        const response = await fetch('/api/cases', { cache: 'no-store', signal: controller.signal });
        if (!response.ok) return;
        const rows: unknown = await response.json();
        if (Array.isArray(rows) && !controller.signal.aborted) {
          setCases(rows.flatMap(row => typeof row?.id === 'string' && isCaseId(row.id) ? [row.id] : []));
        }
      } catch {
        // The saved cases screen provides the detailed retry and recovery actions.
      }
    }
    void loadCases();
    return () => controller.abort();
  }, [canList]);

  function selectView(index: number, focus = false) {
    setView(index);
    if (focus) document.getElementById('sample-view-' + index)?.focus();
  }

  const oneCase = cases?.length === 1 ? cases[0] : null;
  const caseHref = oneCase ? '/cases/' + encodeURIComponent(oneCase) : '/cases/saved';

  return <main className="editorial-home" id="main-content" tabIndex={-1}>
    <section className="container editorial-hero">
      <div className="editorial-intro">
        <p className="editorial-label"><span />{c.region}</p>
        <h1>{c.title}<br/><em>{c.accent}</em></h1>
        <p className="editorial-lead">{c.description}</p>
        <div className="hero-actions">
          <Link href={caseHref} className="button button-primary">
            {oneCase ? c.resume : signedIn && cases?.length !== 0 ? c.cases : c.start}<Icon name="arrowRight"/>
          </Link>
          {syntheticDemo && <Link href="/demo/synthetic" className="editorial-text-link">{c.demo}<Icon name="arrowRight" size={16}/></Link>}
        </div>
        <p className="editorial-independence"><Icon name="shield" size={16}/>{t.independent}</p>
      </div>
      <div className="specimen-stage">
        <div className="specimen-folder">
          <div className="specimen-tab"><Icon name="file" size={16}/>{c.specimen}</div>
          <div className="specimen-paper">
            <div className="specimen-title">
              <div><h2>{c.specimenTitle}</h2></div>
              <span className="specimen-city" aria-hidden="true">MI</span>
            </div>
            <div className="specimen-switch" role="group" aria-label={c.specimen}>
              {c.tabs.map((label, index) => <button key={label} id={'sample-view-' + index} type="button"
                aria-pressed={view === index} aria-controls="sample-content" onClick={() => selectView(index)}>{label}</button>)}
            </div>
            <div id="sample-content" className="specimen-body">
              <div className="specimen-view" key={view}>
                {view === 0 && <>
                  {c.requirements.map((label, index) => <button key={label} type="button" className="specimen-row"
                    aria-pressed={index === requirement} onClick={() => setRequirement(index)}>
                    <Icon name={index ? 'file' : 'home'} size={18}/><strong>{label}</strong><Icon name="arrowRight" size={16}/>
                  </button>)}
                  <div className="specimen-note" aria-live="polite">
                    <strong>{requirement ? c.selected : c.source}</strong><p>{c.explanations[requirement]}</p>
                    {requirement === 1 && <button className="inline-link" type="button" onClick={() => selectView(1, true)}>{c.evidence} →</button>}
                  </div>
                </>}
                {view === 1 && <>
                  <div className="specimen-row specimen-static"><Icon name="file"/><strong>{c.document}</strong><span>{c.page}</span></div>
                  <div className="specimen-comparison">
                    <span>{c.caseValue}<b>05.11.2026</b></span><span>{c.docValue}<b>06.11.2026</b></span>
                  </div>
                  <div className="specimen-note specimen-warning"><Icon name="alert" size={17}/><strong>{c.field} · {c.conflict}</strong></div>
                </>}
                {view === 2 && <>
                  <div className="specimen-row specimen-static"><Icon name="file"/><div><strong>{c.summary}</strong><p>{c.blocked}</p></div></div>
                  <div className="specimen-row specimen-static"><Icon name="external"/><div><strong>{c.official}</strong><p>{c.userOnly}</p></div></div>
                  <button className="inline-link specimen-next" type="button" onClick={() => selectView(1, true)}>{c.backToCheck} →</button>
                </>}
              </div>
            </div>
            <p className="specimen-foot"><Icon name="info" size={15}/>{c.caption}</p>
          </div>
        </div>
      </div>
    </section>
    <section id="how-it-works" className="editorial-how">
      <div className="container editorial-how-inner">
        <div><p className="editorial-label">{c.how}</p><h2>{t.howTitle}</h2></div>
        <div className="editorial-how-list">
          {[[t.howA, t.howAD], [t.howB, t.howBD], [t.howC, t.howCD]].map(([title, description], index) =>
            <article key={title}><span>0{index + 1}</span><div><h3>{title}</h3><p>{description}</p></div></article>)}
        </div>
      </div>
    </section>
    <footer className="site-footer container"><span>© PracticaMIA</span><span>{t.footer}</span></footer>
  </main>;
}
