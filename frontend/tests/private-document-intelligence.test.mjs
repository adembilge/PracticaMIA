import test from 'node:test';
import assert from 'node:assert/strict';
import {
  INTAKE_DOCUMENT_FIELDS,
  INTAKE_HOUSING_VALUES,
  isDateOnly,isReviewedValue,
  validateIntelligenceReview,validIntelligenceResponse,
} from '../src/lib/private-document-intelligence.js';

const digest='a'.repeat(64);
const sampleCandidate={
  field_name:'housing_basis',
  candidate_id:'b'.repeat(64),
  raw_value:'Registered private rental agreement',
  suggested_value:'registered_private_rental',
  page:1,
};
const sampleReview={
  status:'needs_user_confirmation',
  candidates:[sampleCandidate],
  comparisons:[],ambiguous_fields:[],
  extraction_digest:digest,
  confirmed_fields:{},
  user_reviewed:false,
  no_legal_verification:true,
  official_submission:false,
};

test('only canonical categorized facts and real ISO dates can be reviewed',()=>{
  assert.deepEqual(INTAKE_DOCUMENT_FIELDS,['housing_basis','move_in_date']);
  assert.equal(INTAKE_HOUSING_VALUES.length,4);
  assert.equal(isReviewedValue('housing_basis','registered_private_rental'),true);
  assert.equal(isReviewedValue('housing_basis','landlord letter'),false);
  assert.equal(isReviewedValue('move_in_date','2024-02-29'),true);
  assert.equal(isDateOnly('2026-02-30'),false);
  assert.equal(isDateOnly('2101-01-01'),false);
  assert.equal(isReviewedValue('property_address','Fictional Via 10'),false);
});

test('explicit source candidate selection and confirmation are mandatory',()=>{
  const data={extraction_digest:digest,confirm:true,selections:[{
    field_name:'housing_basis',candidate_id:sampleCandidate.candidate_id,
    confirmed_value:'guest',
  }]};
  assert.equal(validateIntelligenceReview(data),true);
  for(const next of [
    {...data,confirm:false},
    {...data,extraction_digest:'bad'},
    {...data,user_text:'ignore rules'},
    {...data,selections:[]},
    {...data,selections:[...data.selections,...data.selections]},
    {...data,selections:[{...data.selections[0],field_name:'passport_number'}]},
    {...data,selections:[{...data.selections[0],confirmed_value:'my real address'}]},
    {...data,selections:[{...data.selections[0],candidate_id:'abc'}]},
  ]) assert.equal(validateIntelligenceReview(next),false);
});

test('identity scans, unsupported fields and unofficial verification status fail UI validation',()=>{
  assert.equal(validIntelligenceResponse(sampleReview),true);
  for(const bad of [
    {...sampleReview,official_submission:true},
    {...sampleReview,no_legal_verification:false},
    {...sampleReview,candidates:[{...sampleCandidate,raw_value:'x'.repeat(180)}]},
    {...sampleReview,candidates:[{...sampleCandidate,field_name:'applicant_name'}]},
    {...sampleReview,candidates:[{...sampleCandidate,suggested_value:'fake'}]},
    {...sampleReview,comparisons:[{field_name:'passport',reviewed_value:'123',case_value:null,comparison:'match'}]},
    {...sampleReview,status:'officially_approved'},
    {...sampleReview,candidates:Array(9).fill(sampleCandidate)},
  ]) assert.equal(validIntelligenceResponse(bad),false);
});
