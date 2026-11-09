import test from 'node:test';
import assert from 'node:assert/strict';
import {
  FIRST_ROUTE_VERSION_IDS,SIGNED_ACTION_IDS,
  verifiedChecklistEvidence,validateCaseChecklist,
} from '../src/lib/case-checklist.js';
import {FIRST_ROUTE_SOURCE_LINKS} from '../src/lib/approved-source-view.js';

const sample=(id,source='milano-italian-residence-change')=>({
  id,description:'Exact approved rule text from immutable catalog',
  status:'needs_user',obligation_class:'reviewed_action',
  evidence:[{
    source_id:source,source_version_id:FIRST_ROUTE_VERSION_IDS[source],
    citation_id:FIRST_ROUTE_VERSION_IDS[source]+':0003',
    official_url:FIRST_ROUTE_SOURCE_LINKS[source].url,
    title:'Official referenced snapshot',institution:'Reviewed source',
    reviewed_at:'2026-11-08T00:11:00+00:00',
    archived_reference:source==='anpr-public-docs-residence-guide',
  }],
});
const complete=()=>({
  status:'ready_for_user_review',
  next_action:'Review official sources',
  items:SIGNED_ACTION_IDS.map((id,i)=>sample(id,i>1?'anpr-public-docs-residence-guide':'milano-italian-residence-change')),
  ruleset_version:'milan_italian_individual_registered_rental_v1_20261108',
  verified_evidence:true,synthetic_only:true,first_scenario_only:true,
  eligibility_evaluated:false,documents_verified:false,government_submitted:false,
  required_document_types:[],missing_fields:[],
});

test('five signed reviewed actions display with only pinned official references',()=>{
  assert.equal(SIGNED_ACTION_IDS.length,5);
  assert.equal(validateCaseChecklist(complete()),true);
  assert.equal(verifiedChecklistEvidence(sample(SIGNED_ACTION_IDS[0]).evidence[0]),true);
});

test('an untrusted source, source-version mismatch or forged URL fails closed',()=>{
  for(const changed of [
    {official_url:'https://evil.example.test/replacement'},
    {source_version_id:'new-unknown-version'},
    {citation_id:'bad-citation'},
    {source_id:'external-unknown'},
    {archived_reference:true},
    {reviewed_at:'not-a-date'},
  ]){
    const d=complete();
    Object.assign(d.items[0].evidence[0],changed);
    assert.equal(validateCaseChecklist(d),false,JSON.stringify(changed));
  }
});

test('unchecked, additional, invented or duplicated rules cannot appear as trusted',()=>{
  const tampered=[
    d=>{d.items[0].id='invented_landlord_declaration';},
    d=>{d.items[0].status='verified';},
    d=>{d.items[0].description='x'.repeat(301);},
    d=>{d.items[0].evidence=[];},
    d=>{d.items[1].id=d.items[0].id;},
    d=>{d.required_document_types=['utility_bill'];},
    d=>{d.ruleset_version='unapproved';},
    d=>{d.government_submitted=true;},
    d=>{d.eligibility_evaluated=true;},
  ];
  for(const edit of tampered){
    const d=complete();
    edit(d);
    assert.equal(validateCaseChecklist(d),false);
  }
});

test('blocked or not-confirmed states have no actionable requirements',()=>{
  for(const status of ['needs_scope','needs_confirmation','outside_first_route','evidence_unavailable']){
    const d={...complete(),status,items:[],verified_evidence:false};
    assert.equal(validateCaseChecklist(d),true);
    assert.equal(validateCaseChecklist({...d,items:[sample(SIGNED_ACTION_IDS[0])]}),false);
  }
  assert.equal(validateCaseChecklist(null),false);
  assert.equal(validateCaseChecklist({status:'ready_for_user_review'}),false);
});
