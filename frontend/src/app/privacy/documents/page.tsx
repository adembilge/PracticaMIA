import Link from 'next/link';

export const metadata = {
  title: 'Document privacy — PracticaMIA',
  description: 'The preparation document vault and retention terms.',
};

export default function DocumentPrivacyPage() {
  const published = process.env.PRIVATE_DOCUMENT_PRIVACY_APPROVED === '1' &&
    Boolean(process.env.PRIVATE_DOCUMENT_CONTROLLER?.trim()) &&
    Boolean(process.env.PRIVATE_DOCUMENT_CONTACT?.trim());
  const controller = published ? process.env.PRIVATE_DOCUMENT_CONTROLLER : null;
  const contact = published ? process.env.PRIVATE_DOCUMENT_CONTACT : null;
  return <main className="subpage-background" id="main-content">
    <div className="container account-shell" style={{maxWidth: 760}}>
      <h1 className="subpage-title">Document privacy / Privacy dei documenti</h1>
      {!published && <p role="status"><strong>Document uploads are not open to real users yet.</strong> This is a technical notice draft pending operator and legal review. Non inviare documenti personali.</p>}
      <p><strong>Operator / Titolare:</strong> {controller ?? 'To be confirmed before activation / Da confermare prima dell’attivazione'}</p>
      <p><strong>Contact / Contatto privacy:</strong> {contact ?? 'To be confirmed before activation / Da confermare prima dell’attivazione'}</p>
      <h2>What is processed / Dati trattati</h2>
      <p>If enabled, the vault temporarily stores user-selected PDF, PNG, and JPEG documents for the signed-in case owner. Upload is optional. Documents are not sent to the AI assistant or to government systems.</p>
      <p>Se abilitato, l’archivio conserva temporaneamente PDF, PNG e JPEG scelti dall’utente. I documenti non vengono inviati all’assistente AI né a enti pubblici.</p>
      <h2>Security and retention / Sicurezza e conservazione</h2>
      <p>Files are checked by a contracted malware-scanning service before encryption and database storage. A positive clean verdict is required. Stored documents are visible only to the owning account. Access expires seven days after upload; the scheduled purge removes expired encrypted files, with deletion also available on demand. Backup and disaster-recovery copies may persist for the infrastructure provider’s retention period.</p>
      <p>I file vengono analizzati da un servizio antivirus prima della cifratura. L’accesso scade dopo sette giorni; la cancellazione programmata elimina i file scaduti. L’utente può cancellarli prima. Le copie di backup possono persistere secondo i periodi del fornitore.</p>
      <h2>Limits / Limiti</h2>
      <p>Stored files are not legally validated and do not prove eligibility, required attachments, government filing, or municipal acceptance. The operator must publish its legal basis, processors, recipients, international transfers, rights procedures and full privacy terms before real-user activation. A checkbox confirms that the user has read this notice; it does not itself establish the GDPR legal basis.</p>
      <p>I documenti non sono convalidati giuridicamente e il caricamento non costituisce presentazione ufficiale. Le informazioni complete sul trattamento devono essere pubblicate prima dell’attivazione.</p>
      <p><Link href="/cases/saved" className="inline-link">Return to saved cases / Torna alle pratiche</Link></p>
    </div>
  </main>;
}
