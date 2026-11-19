export type OfficialHandoff = {
  language: 'en' | 'it';
  status: 'verified_channel' | 'verification_required';
  official_channel: { label: string; url: string } | null;
  next_action: { label: string; operation: 'open_official_channel' | 'provide_information' };
  submission_status: 'unconfirmed';
};

const copy = {
  en: {
    title: 'Official handoff',
    submission: 'Official submission',
    unconfirmed: 'Unconfirmed',
    responsibility: 'Complete any required sign-in, signing, payment and submission yourself through the official service.',
  },
  it: {
    title: 'Passaggio al canale ufficiale',
    submission: 'Invio ufficiale',
    unconfirmed: 'Non confermato',
    responsibility: 'Accedi, firma, paga e invia personalmente tramite il servizio ufficiale, quando richiesto.',
  },
} as const;

export function AgentOfficialHandoff({handoff}: {handoff: OfficialHandoff}) {
  const text = copy[handoff.language];
  const channel = handoff.status === 'verified_channel' ? handoff.official_channel : null;
  const openChannel = channel && handoff.next_action.operation === 'open_official_channel';
  return (
    <section aria-label={text.title} lang={handoff.language}>
      <h3>{text.title}</h3>
      {!openChannel && <p>{handoff.next_action.label}</p>}
      {channel && (
        <>
          <a href={channel.url} target="_blank" rel="noopener noreferrer">
            {openChannel ? `${handoff.next_action.label} · ${channel.label}` : channel.label}
          </a>
          <p>{text.responsibility}</p>
        </>
      )}
      <dl>
        <dt>{text.submission}</dt>
        <dd>{text[handoff.submission_status]}</dd>
      </dl>
    </section>
  );
}
