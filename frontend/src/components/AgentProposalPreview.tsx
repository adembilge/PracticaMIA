'use client';

import {useId} from 'react';

type Language = 'en' | 'it';
type ProposalValue = string | number | boolean;

export type PendingProposal = {
  proposal_id: string;
  field_id: string;
  previous_value: ProposalValue | null;
  proposed_value: ProposalValue;
  rationale: string;
  expected_case_revision: number;
};

const copy = {
  en: {
    heading: 'Review proposed change', field: 'Affected field', previous: 'Existing value at this revision',
    proposed: 'Proposed value', rationale: 'Reason for the change', revision: 'Case revision',
    id: 'Proposal ID', empty: 'No value saved', yes: 'Yes', no: 'No',
  },
  it: {
    heading: 'Esamina la modifica proposta', field: 'Campo interessato', previous: 'Valore esistente a questa revisione',
    proposed: 'Valore proposto', rationale: 'Motivo della modifica', revision: 'Revisione della pratica',
    id: 'ID della proposta', empty: 'Nessun valore salvato', yes: 'Sì', no: 'No',
  },
};

const fieldLabels: Readonly<Partial<Record<string, Record<Language, string>>>> = {
  citizenship_class: {en: 'Citizenship category', it: 'Categoria di cittadinanza'},
  registration_context: {en: 'Registration context', it: 'Situazione anagrafica'},
  destination_municipality: {en: 'Destination municipality', it: 'Comune di destinazione'},
  household_scope: {en: 'Household scope', it: 'Situazione del nucleo familiare'},
  housing_basis: {en: 'Housing arrangement', it: 'Titolo di occupazione'},
  move_in_date: {en: 'Move-in date', it: 'Data del trasferimento'},
};

function displayValue(value: ProposalValue | null, labels: typeof copy.en) {
  if (value === null) return labels.empty;
  if (typeof value === 'boolean') return value ? labels.yes : labels.no;
  return String(value);
}

export function AgentProposalPreview({proposal, language}: {proposal: PendingProposal; language: Language}) {
  const heading = useId();
  const labels = copy[language];
  const fieldLabel = Object.hasOwn(fieldLabels, proposal.field_id) ? fieldLabels[proposal.field_id]?.[language] : undefined;
  return (
    <section aria-labelledby={heading} lang={language} className="case-state" style={{overflowWrap: 'anywhere'}}>
      <h2 id={heading}>{labels.heading}</h2>
      <dl>
        <dt>{labels.field}</dt>
        <dd>{fieldLabel && <>{fieldLabel} </>}<code>{proposal.field_id}</code></dd>
        <dt>{labels.previous}</dt>
        <dd>{displayValue(proposal.previous_value, labels)}</dd>
        <dt>{labels.proposed}</dt>
        <dd>{displayValue(proposal.proposed_value, labels)}</dd>
        <dt>{labels.rationale}</dt>
        <dd>{proposal.rationale}</dd>
        <dt>{labels.revision}</dt>
        <dd>{proposal.expected_case_revision}</dd>
        <dt>{labels.id}</dt>
        <dd><code>{proposal.proposal_id}</code></dd>
      </dl>
    </section>
  );
}
