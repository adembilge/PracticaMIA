import test from 'node:test';
import assert from 'node:assert/strict';
import {
  validCaseWorkflow,validReviewMark,WORKFLOW_STEPS,
} from '../src/lib/case-workflow.js';
import {SIGNED_ACTION_IDS,FIRST_ROUTE_VERSION_IDS}
  from '../src/lib/case-checklist.js';
import {FIRST_ROUTE_SOURCE_LINKS} from '../src/lib/approved-source-view.js';

const source='milano-italian-residence-change';
const version=FIRST_ROUTE_VERSION_IDS[source];
const citation={
  citation_id:version+':0001',source_id:source,source_version_id:version,
  official_url:FIRST_ROUTE_SOURCE_LINKS[source].url,
  title:'Reviewed official source',reviewed_at:'2026-11-08T11:00:00+00:00',
  archived_reference:false,
};

const statuses=[
  'complete','complete','informational','needs_attention',
  'unavailable','draft_available','user_only_not_submitted',
];
function state(){
  return {
    case_reference:'ca5e2026',workflow_version:'case-journey-v1',
    steps:WORKFLOW_STEPS.map((id,i)=>({id,status:statuses[i]})),
    next_action:'review_checklist',scope_status:'provisionally_in_scope',
    intake_confirmed:true,
    checklist:{
      status:'ready_for_user_review',
      items:SIGNED_ACTION_IDS.map(id=>({
        id,status:'needs_user',description:'Signed action from reviewed catalog',
        evidence:[citation],
      })),
      ruleset_version:'milan_italian_individual_registered_rental_v1_20261108',
      reviewed_items:{},reviewed_count:0,total:5,
      fingerprint:'a'.repeat(64),
    },
    package:{
      status:'reviewable_draft',download_allowed:true,
      outstanding_issues:['private_document_processing_not_enabled'],
    },
    documents:{enabled:false,uploaded_count:0,reviewed_count:0,
      legal_verification:false},
    official_submission:false,eligibility_evaluated:false,synthetic_only:true,
  };
}

test('signed reviewable user journey is validated without official approval',()=>{
  assert.equal(WORKFLOW_STEPS.length,7);
  assert.equal(validCaseWorkflow(state()),true);
  const x=state();
  x.checklist.reviewed_items[x.checklist.items[0].id]='2026-11-09T07:00:00+00:00';
  x.checklist.reviewed_count=1;
  assert.equal(validCaseWorkflow(x),true);
});

test('incomplete case exposes no reviewable action or fingerprint',()=>{
  const x=state();
  x.next_action='confirm_intake';
  x.steps[0].status='needs_attention';
  x.steps[1].status='locked';
  x.steps[3].status='locked';
  x.steps[5].status='blocked';
  x.checklist={
    status:'unavailable',items:[],ruleset_version:null,
    reviewed_items:{},reviewed_count:0,total:0,fingerprint:null,
  };
  x.package={status:'blocked',download_allowed:false,
    outstanding_issues:['checklist_needs_confirmation']};
  assert.equal(validCaseWorkflow(x),true);
  assert.equal(validCaseWorkflow({...x,package:{
    ...x.package,download_allowed:true,
  }}),false);
});

test('tampering signed citations, checklist marks or official status fails closed',()=>{
  const changes=[
    x=>{x.official_submission=true;},
    x=>{x.eligibility_evaluated=true;},
    x=>{x.steps[0].id='unknown';},
    x=>{x.next_action='auto_submit_to_Anpr';},
    x=>{x.checklist.items[0].id='new-unapproved-rule';},
    x=>{x.checklist.items[0].evidence[0]={...citation,
      official_url:'https://phishing.example.test/'};},
    x=>{x.checklist.reviewed_items.fake='2026-11-09T07:00:00Z';
      x.checklist.reviewed_count=1;},
    x=>{x.checklist.fingerprint='invalid';},
    x=>{x.package.outstanding_issues=['invented_requirement'];},
    x=>{x.documents.legal_verification=true;},
  ];
  for(const change of changes){
    const x=state();
    change(x);
    assert.equal(validCaseWorkflow(x),false);
  }
});

test('review mark is strictly a boolean on one signed action, not client facts',()=>{
  const valid={
    item_id:SIGNED_ACTION_IDS[0],reviewed:true,fingerprint:'f'.repeat(64),
  };
  assert.equal(validReviewMark(valid),true);
  for(const invalid of [
    null,[],{}, {...valid,reviewed:'yes'},
    {...valid,fingerprint:'invalid'}, {...valid,item_id:'new_imagined_requirement'},
    {...valid,source_url:'https://official.example.test/'},
    {...valid,raw_answers:['yes','yes','yes','no','yes']},
    {...valid,government_approval:true},
  ])assert.equal(validReviewMark(invalid),false);
});
