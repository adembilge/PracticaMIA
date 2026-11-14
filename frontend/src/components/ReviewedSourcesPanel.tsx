'use client';

import { useEffect, useState } from 'react';
import {
  FIRST_ROUTE_SOURCE_LINKS, selectReviewedFirstRouteSources,
} from '@/lib/approved-source-view.js';

type Source = {
  source_id: string;
  source_version_id: string;
  title: string;
  official_url: string;
  reviewed_at: string;
  content_sha256: string;
};
type Props = { locale: 'en' | 'it' };

export function ReviewedSourcesPanel({ locale }: Props) {
  const [sources, setSources] = useState<Source[]>([]);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/knowledge/sources', {cache: 'no-store', signal: controller.signal})
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (!controller.signal.aborted) setSources(selectReviewedFirstRouteSources(data)); })
      .catch(() => {})
      .finally(() => { if (!controller.signal.aborted) setLoaded(true); });
    return () => controller.abort();
  }, []);

  const it = locale === 'it';
  const complete = sources.length === 2;
  return <section aria-label={it ? 'Fonti revisionate' : 'Reviewed sources'} style={{marginTop: 20}}>
    <h3>{it ? 'Fonti revisionate per il primo scenario' : 'Reviewed references for this example route'}</h3>
    <p>{it
      ? 'Queste due versioni sono state revisionate e archiviate con impronte digitali verificabili. La revisione non certifica l’attualità di ogni requisito ANPR.'
      : 'These two source versions have recorded reviews and verified hashes. That does not establish the current ANPR form fields or requirements.'}</p>
    {loaded && complete ? <ul style={{paddingLeft: 20, lineHeight: 1.65}}>
      {sources.map(source => <li key={source.source_id} style={{marginBottom: 8}}>
        <a className="inline-link" target="_blank" rel="noopener noreferrer"
           href={FIRST_ROUTE_SOURCE_LINKS[source.source_id as keyof typeof FIRST_ROUTE_SOURCE_LINKS].url}>
          {source.title}
        </a>
        {' — '}
        {source.source_id === 'anpr-public-docs-residence-guide'
          ? (it ? 'edizione archiviata (non confermata come versione ANPR attuale)' : 'archived edition (not confirmed current)')
          : (it ? 'versione del Comune revisionata' : 'reviewed municipal snapshot')}
      </li>)}
    </ul> : loaded ? <p role="status">
      {it ? 'Non tutte le fonti revisionate sono disponibili. Controlla direttamente i siti ufficiali.'
          : 'Not all reviewed sources are available. Check the official websites directly.'}
    </p> : <p role="status">{it ? 'Caricamento delle fonti…' : 'Loading reviewed sources…'}</p>}
    <p style={{fontSize: 12, opacity: 0.8}}>
      {it ? 'La revisione interna non è un’approvazione comunale, né una verifica personale dei documenti.'
          : 'Internal review is not municipal endorsement or verification of your personal documents.'}
    </p>
  </section>;
}
