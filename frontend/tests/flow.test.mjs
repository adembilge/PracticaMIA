import assert from 'node:assert/strict';
import test from 'node:test';
import { classifyScope, classifySingleAnswer, validateIntake, sameAddressWarning } from '../src/lib/flow.js';

test('matching responses are only provisionally within demo scope', () => {
  assert.equal(classifyScope(['yes', 'yes', 'yes', 'no', 'yes']), 'provisionally_in_scope');
});

test('incomplete answers do not imply approval', () => {
  assert.equal(classifyScope(['yes', 'yes']), 'incomplete');
});

test('unknown registration pauses the flow', () => {
  assert.equal(classifyScope(['unsure']), 'needs_information');
  assert.equal(classifySingleAnswer(0, 'unsure'), 'needs_information');
});

test('moving out of Milan and household merger are out of demo scope', () => {
  assert.equal(classifySingleAnswer(1, 'no'), 'unsupported');
  assert.equal(classifySingleAnswer(3, 'yes'), 'unsupported');
});

test('intake requires addresses and valid move date', () => {
  assert.deepEqual(validateIntake({ previousAddress: '', newAddress: 'Via Esempio 10', movedOn: '' }), {
    previousAddress: 'required',
    movedOn: 'required',
  });
  assert.deepEqual(validateIntake({ previousAddress: 'A', newAddress: 'B', movedOn: '2026-11-02' }), {});
});

test('same entered addresses are flagged for review', () => {
  assert.equal(sameAddressWarning({ previousAddress: 'Via Esempio 12', newAddress: ' via esempio 12 ' }), true);
  assert.equal(sameAddressWarning({ previousAddress: 'A', newAddress: 'B' }), false);
});

test('impossible calendar date is rejected', () => {
  assert.deepEqual(validateIntake({ previousAddress: 'A', newAddress: 'B', movedOn: '2026-02-30' }), { movedOn: 'invalid' });
});
