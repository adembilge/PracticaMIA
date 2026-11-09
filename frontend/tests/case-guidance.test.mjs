import test from 'node:test';
import assert from 'node:assert/strict';
import {
  parseStoredCase, getCaseGuidancePlan, validateCaseGuidanceRequest,
  makeCaseGuidanceMessages,
} from '../src/lib/case-guidance.js';

const id='11111111-1111-4111-8111-111111111111';
const caseRecord=(answers,status)=>({
  id,procedure:'milan_residence_change',status,scope_answers:answers,
  owner_subject:'NEVER_SEND_OWNER', previous_address:'NEVER_SEND_ADDRESS',
});
const request={topic:'next_step',language:'en'};

test('new saved case asks for the first scope answer and preserves its draft state',()=>{
  const saved=parseStoredCase(caseRecord([],'draft'),id);
  assert.ok(saved);
  assert.equal(saved.status,'draft');
  const plan=getCaseGuidancePlan(saved);
  assert.equal(plan.status,'incomplete');
  assert.equal(plan.next_question_index,0);
  assert.equal(plan.answered_count,0);
  assert.equal(plan.authoritative_check,false);
  assert.equal(plan.official_submission,false);
  assert.equal(plan.personalized_documents_verified,false);
});

test('actual scope answers determine different case-specific next actions',()=>{
  const partial=getCaseGuidancePlan(parseStoredCase(caseRecord(['yes','yes'],'incomplete'),id));
  assert.equal(partial.next_question_index,2);
  assert.equal(partial.answered_count,2);
  const unsure=getCaseGuidancePlan(parseStoredCase(caseRecord(['yes','unsure'],'needs_information'),id));
  assert.equal(unsure.next_question_index,1);
  assert.match(unsure.next_step,/Clarify/);
  const unsupported=getCaseGuidancePlan(parseStoredCase(caseRecord(['no'],'unsupported'),id));
  assert.equal(unsupported.next_question_index,0);
  assert.match(unsupported.summary,/does not mean.*ineligible/);
  const complete=getCaseGuidancePlan(parseStoredCase(caseRecord(['yes','yes','yes','no','yes'],'provisionally_in_scope'),id),'it');
  assert.equal(complete.next_question_index,null);
  assert.equal(complete.completed,true);
  assert.equal(complete.answers[3].answer,'no');
  assert.match(complete.next_step,/ANPR/);
  assert.equal(complete.personalized_documents_verified,false);
});

test('saved case cannot be impersonated or overwritten by client-supplied answers',()=>{
  assert.equal(parseStoredCase(caseRecord(['yes'],'incomplete'),'22222222-2222-4222-8222-222222222222'),null);
  assert.equal(parseStoredCase(caseRecord(['yes','yes','yes','no','yes'],'unsupported'),id),null);
  assert.equal(parseStoredCase(caseRecord(['maybe'],'incomplete'),id),null);
  assert.equal(parseStoredCase(caseRecord(Array(6).fill('yes'),'incomplete'),id),null);
  assert.equal(parseStoredCase({...caseRecord([],'draft'),procedure:'another_case'},id),null);
  assert.equal(getCaseGuidancePlan({status:'provisionally_in_scope',answers:['yes']}),null);
});

test('request schema rejects free text and arbitrary personal data',()=>{
  assert.deepEqual(validateCaseGuidanceRequest(request),request);
  assert.deepEqual(validateCaseGuidanceRequest({topic:'explain_status',language:'it'}),{
    topic:'explain_status',language:'it',
  });
  for(const value of [
    null,[],{}, {topic:'next_step'},{topic:'next_step',language:'fr'},
    {topic:'documents',language:'en'},
    {...request,question:'MY_REAL_ADDRESS'},
    {...request,case_answers:['yes','yes','yes','no','yes']},
    {...request,name:'PRIVATE_NAME'},
  ]) assert.equal(validateCaseGuidanceRequest(value),null);
});

test('OpenRouter prompt contains ONLY abstract workflow state and question number',()=>{
  for(const [answers,status] of [
    [[], 'draft'], [['yes'],'incomplete'],
    [['yes','unsure'],'needs_information'],
    [['no'],'unsupported'],
    [['yes','yes','yes','no','yes'],'provisionally_in_scope'],
  ]) {
    const saved=parseStoredCase(caseRecord(answers,status),id);
    const plan=getCaseGuidancePlan(saved);
    const messages=makeCaseGuidanceMessages(plan,request);
    assert.equal(messages.length,2);
    const payload=JSON.stringify(messages);
    for(const prohibited of [
      id,'NEVER_SEND_OWNER','NEVER_SEND_ADDRESS','scope_answers','previous_address',
      'property address','person@example.com',
    ]) assert.ok(!payload.includes(prohibited),prohibited);
    assert.ok(!payload.includes(JSON.stringify(answers)),'Raw answers leaked');
    assert.match(payload,/NOT an official authority/);
    assert.match(payload,/No personal data|no personal data/i);
  }
});

test('Italian and English explanations are case-state dependent, not legal decisions',()=>{
  const caseData=parseStoredCase(caseRecord(['yes','yes','yes','no','yes'],'provisionally_in_scope'),id);
  const plan=getCaseGuidancePlan(caseData,'it');
  const messages=makeCaseGuidanceMessages(plan,{topic:'explain_status',language:'it'});
  assert.match(messages[0].content,/Respond in Italian/);
  assert.match(messages[1].content,/All five product scope questions/);
  assert.equal(makeCaseGuidanceMessages(plan,{topic:'anything',language:'en'}),null);
});
