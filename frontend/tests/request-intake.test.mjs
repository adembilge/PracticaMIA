import assert from 'node:assert/strict';
import test from 'node:test';
import {INTAKE_FIELDS,FIRST_ROUTE_FACTS,isRequestIntakePayload,requestIntakeState,isRealCalendarDate}
  from '../src/lib/request-intake.js';

test('request details accept only bounded categorical facts and valid dates',()=>{
  assert.equal(INTAKE_FIELDS.length,5);
  assert.equal(isRequestIntakePayload({facts:FIRST_ROUTE_FACTS,confirm:true}),true);
  assert.equal(isRequestIntakePayload({facts:{},confirm:false}),true);
  assert.equal(isRequestIntakePayload({facts:{citizenship_class:'unknown'},confirm:true}),false);
  for(const key of ['name','address','postcode','passport_number','lease_pdf','prompt']){
    assert.equal(isRequestIntakePayload({facts:{...FIRST_ROUTE_FACTS,[key]:'private'},confirm:true}),false);
  }
  for(const value of ['2026-02-30','1900-02-29','1999-13-01','2026/01/01','not-a-date','2101-01-01']){
    assert.equal(isRealCalendarDate(value),false);
  }
  assert.equal(isRealCalendarDate('2024-02-29'),true);
  assert.equal(isRequestIntakePayload({facts:{...FIRST_ROUTE_FACTS,move_in_date:'2024-02-29'},confirm:true}),true);
  assert.equal(isRequestIntakePayload({facts:{...FIRST_ROUTE_FACTS},confirm:'true'}),false);
  assert.equal(isRequestIntakePayload({facts:{...FIRST_ROUTE_FACTS},confirm:true,secret:'x'}),false);
});

test('confirmed request facts are distinct from eligibility',()=>{
  assert.equal(requestIntakeState({},false),'incomplete');
  assert.equal(requestIntakeState(FIRST_ROUTE_FACTS,false),'needs_confirmation');
  assert.equal(requestIntakeState(FIRST_ROUTE_FACTS,true),'confirmed');
  assert.equal(requestIntakeState({...FIRST_ROUTE_FACTS,housing_basis:'guest'},true),'outside_first_scenario');
});
