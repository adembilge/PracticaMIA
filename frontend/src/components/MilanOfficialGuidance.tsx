import { MILAN_OFFICIAL_LINKS, MILAN_GUIDANCE_SNAPSHOT } from '@/lib/milan-official-guidance.js';

type Props = { locale: 'en' | 'it' };

const copy = {
  en: {
    eyebrow: 'NEXT STEP · OFFICIAL SOURCES',
    title: 'Continue on the official Milan service',
    lead: 'Your answers match only this product’s narrow example route. PracticaMIA has not checked your identity, eligibility, documents or municipal records.',
    steps: [
      'Read the current Comune di Milano guidance. Its published instructions say residents should report a move within 20 days.',
      'Access the ANPR service using the digital identity method accepted by the official portal (including SPID or CIE). Check the attachments requested for your exact situation there.',
      'Check the separate TARI (waste-tax) declaration instructions. Completing this case here does not submit either declaration.',
    ],
    service: 'Comune di Milano · Change of residence',
    faq: 'Comune di Milano · Italian-citizen FAQ',
    anpr: 'Open the national ANPR website',
    documents: 'Supporting documents: not verified by PracticaMIA',
    docText: 'The official portal determines what supporting material applies. Do not upload identity documents into this demonstration. Review any current requirements directly on ANPR.',
    foot: 'Public information links checked on',
    footer: 'This is a preparation reference, not a municipal decision, verified checklist or submission receipt.',
  },
  it: {
    eyebrow: 'PROSSIMO PASSO · FONTI UFFICIALI',
    title: 'Prosegui sul servizio ufficiale del Comune di Milano',
    lead: 'Le risposte corrispondono soltanto allo scenario limitato di questa dimostrazione. PracticaMIA non ha verificato identità, requisiti, documenti o registri comunali.',
    steps: [
      'Consulta le istruzioni attuali del Comune di Milano. Secondo le indicazioni pubblicate, il trasferimento va comunicato entro 20 giorni.',
      'Accedi al servizio ANPR con un’identità digitale accettata dal portale ufficiale, tra cui SPID o CIE. Verifica lì gli allegati richiesti per il tuo caso.',
      'Controlla separatamente le indicazioni per la dichiarazione TARI. Concludere questa pratica non invia alcuna dichiarazione.',
    ],
    service: 'Comune di Milano · Cambio di residenza',
    faq: 'Comune di Milano · FAQ cittadini italiani',
    anpr: 'Apri il sito nazionale ANPR',
    documents: 'Documenti necessari: non verificati da PracticaMIA',
    docText: 'Gli allegati applicabili dipendono dalle istruzioni ufficiali e dalla situazione personale. Non caricare documenti di identità in questa dimostrazione; consulta direttamente ANPR.',
    foot: 'Collegamenti alle informazioni pubbliche controllati il',
    footer: 'Questo è un riferimento preparatorio, non una decisione comunale, un elenco verificato o una ricevuta di invio.',
  },
} as const;

export function MilanOfficialGuidance({locale}: Props) {
  const t = copy[locale];
  return <section aria-label={t.title} style={{padding: 18, marginTop: 20, border: '1px solid #dae4e7', borderRadius: 12}}>
    <span className="tiny-eyebrow">{t.eyebrow}</span>
    <h3 style={{marginTop: 9}}>{t.title}</h3>
    <p>{t.lead}</p>
    <ol style={{paddingLeft: 21, lineHeight: 1.65}}>
      {t.steps.map(x => <li key={x} style={{marginBottom: 10}}>{x}</li>)}
    </ol>
    <nav aria-label={t.title} style={{display: 'flex', flexDirection: 'column', gap: 9, marginTop: 14}}>
      <a className="inline-link" target="_blank" rel="noopener noreferrer" href={MILAN_OFFICIAL_LINKS.service}>{t.service}</a>
      <a className="inline-link" target="_blank" rel="noopener noreferrer" href={MILAN_OFFICIAL_LINKS.faq}>{t.faq}</a>
      <a className="inline-link" target="_blank" rel="noopener noreferrer" href={MILAN_OFFICIAL_LINKS.anpr}>{t.anpr}</a>
    </nav>
    <div className="message-box notice" style={{marginTop: 16}}>
      <div><strong>{t.documents}</strong><p>{t.docText}</p></div>
    </div>
    <p style={{fontSize: 12, opacity: 0.8, marginTop: 14}}>
      {t.foot} {MILAN_GUIDANCE_SNAPSHOT}. {t.footer}
    </p>
  </section>;
}
