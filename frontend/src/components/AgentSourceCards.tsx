'use client';

import {useEffect, useId, useRef, useState} from 'react';

type Language = 'en' | 'it';

export type AgentCitation = {
  citation_id: string;
  publisher: string;
};

type SourceCardDetails = {
  title: string;
  source_language: Language;
  explanation_language: Language;
  passage: {
    citation: {citation_id: string; official_url: string};
    section_path: string;
    content: string;
    source_revision: number;
  };
  terms: {term: string; explanation: string}[];
};

const copy = {
  en: {
    sources: 'Sources', open: 'View cited passage', close: 'Close cited passage',
    loading: 'Loading the cited passage…', unavailable: 'This cited passage is unavailable.',
    revision: 'Source revision', terms: 'Italian terms', official: 'Open the official page',
  },
  it: {
    sources: 'Fonti', open: 'Visualizza il passaggio citato', close: 'Chiudi il passaggio citato',
    loading: 'Caricamento del passaggio citato…', unavailable: 'Il passaggio citato non è disponibile.',
    revision: 'Revisione della fonte', terms: 'Termini italiani', official: 'Apri la pagina ufficiale',
  },
};

function SourceCard({runUrl, citation, language}: {
  runUrl: string; citation: AgentCitation; language: Language;
}) {
  const id = useId();
  const request = useRef<AbortController | null>(null);
  const [details, setDetails] = useState<SourceCardDetails | 'loading' | 'unavailable' | null>(null);
  const labels = copy[language];

  useEffect(() => () => request.current?.abort(), []);

  async function toggle() {
    if (details !== null) {
      request.current?.abort();
      setDetails(null);
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    setDetails('loading');
    try {
      const response = await fetch(`${runUrl}/sources/${encodeURIComponent(citation.citation_id)}`, {
        cache: 'no-store', signal: controller.signal,
      });
      if (!response.ok) throw new Error('Cited passage unavailable');
      const body: SourceCardDetails = await response.json();
      if (body.passage.citation.citation_id !== citation.citation_id) throw new Error('Citation mismatch');
      if (!controller.signal.aborted) setDetails(body);
    } catch {
      if (!controller.signal.aborted) setDetails('unavailable');
    }
  }

  return (
    <li>
      <p><strong>{citation.publisher}</strong></p>
      <button type="button" aria-expanded={details !== null} aria-controls={id} onClick={() => void toggle()}>
        {details === null ? labels.open : labels.close}
      </button>
      <div id={id} aria-busy={details === 'loading'}>
        {details === 'loading' && <p role="status">{labels.loading}</p>}
        {details === 'unavailable' && <p role="status">{labels.unavailable}</p>}
        {details && typeof details === 'object' && <>
          <h4 lang={details.source_language}>{details.title}</h4>
          <p lang={details.source_language}>{details.passage.section_path}</p>
          <blockquote lang={details.source_language}>
            <p style={{whiteSpace: 'pre-wrap', overflowWrap: 'anywhere'}}>{details.passage.content}</p>
          </blockquote>
          <p>{labels.revision} {details.passage.source_revision}</p>
          {details.terms.length > 0 && <section lang={details.explanation_language}>
            <h5>{copy[details.explanation_language].terms}</h5>
            <dl>{details.terms.map(({term, explanation}) => (
              <div key={term}><dt lang="it">{term}</dt><dd>{explanation}</dd></div>
            ))}</dl>
          </section>}
          <a href={details.passage.citation.official_url}>{labels.official}</a>
        </>}
      </div>
    </li>
  );
}

export function AgentSourceCards({runUrl, citations, language}: {
  runUrl: string; citations: AgentCitation[]; language: Language;
}) {
  const heading = useId();
  if (!citations.length) return null;
  return (
    <section aria-labelledby={heading}>
      <h3 id={heading}>{copy[language].sources}</h3>
      <ul>{citations.map(citation => (
        <SourceCard key={`${runUrl}/${citation.citation_id}`} runUrl={runUrl} citation={citation} language={language} />
      ))}</ul>
    </section>
  );
}
