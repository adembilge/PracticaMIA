import test from 'node:test';
import assert from 'node:assert/strict';
import {validPackageManifest,PREPARATION_ISSUES}
  from '../src/lib/case-package.js';
import {SIGNED_ACTION_IDS,FIRST_ROUTE_VERSION_IDS}
  from '../src/lib/case-checklist.js';
import {FIRST_ROUTE_SOURCE_LINKS} from '../src/lib/approved-source-view.js';

const sourceId='milano-italian-residence-change';
const sourceVersion=FIRST_ROUTE_VERSION_IDS[sourceId];
const evidence={
  citation_id:sourceVersion+':0002',
  source_id:sourceId,source_version_id:sourceVersion,
  official_url:FIRST_ROUTE_SOURCE_LINKS[sourceId].url,
  title:'Reviewed official reference',
  reviewed_at:'2026-11-08T00:11:00+00:00',
  archived_reference:false,
};
const fields=[
  'citizenship_class','registration_context','destination_municipality',
  'household_scope','housing_basis',
];

function manifest(){
  return {
    status:'reviewable_draft',download_allowed:true,
    case_reference:'1a2b3c4d',procedure_id:'milan_residence_change',
    jurisdiction:'IT-MI-MILANO',generated_at:'2026-11-09T12:00:00Z',
    reviewed_ruleset:'milan_italian_individual_registered_rental_v1_20261108',
    confirmed_facts:fields.map(field=>({
      field,label:field,value:'test',provenance:'user_confirmed',
    })),
    checklist:SIGNED_ACTION_IDS.map(id=>({
      id,status:'needs_user',description:'Exact signed rule text',
      evidence:[evidence],
    })),
    documents:[],outstanding_issues:['private_document_processing_not_enabled'],
    official_handoff:{
      anpr_portal:'https://www.anagrafenazionale.interno.it/',
      milan_service:'https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza',
      instruction:'User completes submission on official site',
    },
    document_requirements_verified:false,eligibility_evaluated:false,
    documents_legally_verified:false,official_submission:false,
    official_acceptance:false,draft_only:true,synthetic_only:true,
  };
}

test('reviewable preparation draft is source-pinned and non-official',()=>{
  assert.equal(validPackageManifest(manifest()),true);
  assert.equal(Object.hasOwn(PREPARATION_ISSUES,
    'private_document_processing_not_enabled'),true);
  assert.equal(Object.hasOwn(PREPARATION_ISSUES,
    'document_needs_case_information'),true);
});

test('unsupported application or fabricated approval cannot expose download',()=>{
  const mutations=[
    d=>{d.official_submission=true;},
    d=>{d.official_acceptance=true;},
    d=>{d.document_requirements_verified=true;},
    d=>{d.download_allowed=false;},
    d=>{d.reviewed_ruleset='new-unapproved-version';},
    d=>{d.checklist[0].id='invented-lease-exemption';},
    d=>{d.checklist[1].id=d.checklist[0].id;},
    d=>{d.checklist[0].description='x'.repeat(301);},
    d=>{d.checklist[0].status='approved';},
    d=>{d.checklist[0].evidence[0]={...evidence,official_url:'https://evil.example.test/'};},
    d=>{d.confirmed_facts[0].provenance='verified_by_government';},
    d=>{d.official_handoff.anpr_portal='https://not-anpr.example.test/';},
    d=>{d.outstanding_issues=['unknown_risk_value'];},
    d=>{d.documents=[{number:1,category:'identity_document',
      review_status:'officially_valid',comparisons:[{field:'applicant_name',
        result:'accepted'}]}];},
  ];
  for(const modify of mutations){
    const d=manifest();
    modify(d);
    assert.equal(validPackageManifest(d),false);
  }
});

test('blocked or incomplete cases cannot advertise an export',()=>{
  const blocked={...manifest(),status:'blocked',download_allowed:false,
    checklist:[],confirmed_facts:[],reviewed_ruleset:null,
    outstanding_issues:['checklist_outside_first_route']};
  assert.equal(validPackageManifest(blocked),true);
  assert.equal(validPackageManifest({...blocked,download_allowed:true}),false);
  assert.equal(validPackageManifest({...blocked,outstanding_issues:[]}),false);
});
