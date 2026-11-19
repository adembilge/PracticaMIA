'use client';

import {useId, useState} from 'react';

type Language = 'en' | 'it';
export type ProposalValue = string | number | boolean;
export type ProposalDecision = 'accept' | 'correct' | 'reject' | 'cancel';

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
    accept: 'Accept proposal', correct: 'Correct value', reject: 'Reject proposal', cancel: 'Cancel proposal',
    corrected: 'Corrected value', review: 'Review correction', back: 'Back to proposal',
  },
  it: {
    heading: 'Esamina la modifica proposta', field: 'Campo interessato', previous: 'Valore esistente a questa revisione',
    proposed: 'Valore proposto', rationale: 'Motivo della modifica', revision: 'Revisione della pratica',
    id: 'ID della proposta', empty: 'Nessun valore salvato', yes: 'Sì', no: 'No',
    accept: 'Accetta la proposta', correct: 'Correggi il valore', reject: 'Rifiuta la proposta',
    cancel: 'Annulla la proposta', corrected: 'Valore corretto', review: 'Esamina la correzione',
    back: 'Torna alla proposta',
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

export function AgentProposalPreview({proposal, language, busy, onDecision}: {
  proposal: PendingProposal;
  language: Language;
  busy: boolean;
  onDecision: (decision: ProposalDecision, value?: ProposalValue) => void;
}) {
  const heading = useId();
  const labels = copy[language];
  const fieldLabel = Object.hasOwn(fieldLabels, proposal.field_id) ? fieldLabels[proposal.field_id]?.[language] : undefined;
  const [editing, setEditing] = useState(false);
  const [correction, setCorrection] = useState(String(proposal.proposed_value));
  const valueType = typeof proposal.proposed_value;
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
      {editing ? (
        <form onSubmit={event => {
          event.preventDefault();
          const value = valueType === 'boolean' ? correction === 'true'
            : valueType === 'number' ? Number(correction) : correction.trim();
          onDecision('correct', value);
        }}>
          <label>
            {labels.corrected}
            {valueType === 'boolean' ? (
              <select value={correction} onChange={event => setCorrection(event.target.value)} disabled={busy}>
                <option value="true">{labels.yes}</option>
                <option value="false">{labels.no}</option>
              </select>
            ) : (
              <input type={valueType === 'number' ? 'number' : proposal.field_id === 'move_in_date' ? 'date' : 'text'}
                maxLength={300} required value={correction} onChange={event => setCorrection(event.target.value)}
                disabled={busy} />
            )}
          </label>
          <button type="submit" disabled={busy || !correction.trim()}>{labels.review}</button>
          <button type="button" disabled={busy} onClick={() => setEditing(false)}>{labels.back}</button>
        </form>
      ) : (
        <div>
          <button type="button" disabled={busy} onClick={() => onDecision('accept')}>{labels.accept}</button>
          <button type="button" disabled={busy} onClick={() => setEditing(true)}>{labels.correct}</button>
          <button type="button" disabled={busy} onClick={() => onDecision('reject')}>{labels.reject}</button>
          <button type="button" disabled={busy} onClick={() => onDecision('cancel')}>{labels.cancel}</button>
        </div>
      )}
    </section>
  );
}
