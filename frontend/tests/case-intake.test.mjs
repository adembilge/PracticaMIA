import assert from 'node:assert/strict';
import test from 'node:test';
import {INTAKE_FIELDS, FIRST_ROUTE_FACTS, isCaseIntakePayload,
        firstRouteIntakeState, isRealCalendarDate} from '../src/lib/case-intake.js';

test('only typed, bounded categorical facts and dates are supported',()=>{
  assert.equal(INTAKE_FIELDS.length,5);
  assert.equal(isCaseIntakePayload({facts:FIRST_ROUTE_FACTS,confirm:true}),true);
  assert.equal(isCaseIntakePayload({facts:{},confirm:false}),true);
  assert.equal(isCaseIntakePayload({facts:{citizenship_class:'unknown'},confirm:false}),true);
  assert.equal(isCaseIntakePayload({facts:{citizenship_class:'unknown'},confirm:true}),false);
  for(const key of ['name','address','postcode','passport_number','lease_pdf','prompt']){
    assert.equal(isCaseIntakePayload({facts:{...FIRST_ROUTE_FACTS,[key]:'private'},confirm:true}),false);
  }
  for(const value of ['2026-02-30','1900-02-29','1999-13-01','2026/01/01','not-a-date','2101-01-01']){
    assert.equal(isRealCalendarDate(value),false);
  }
  assert.equal(isRealCalendarDate('2024-02-29'),true);
  assert.equal(isCaseIntakePayload({facts:{...FIRST_ROUTE_FACTS,move_in_date:'2024-02-29'},confirm:true}),true);
  assert.equal(isCaseIntakePayload({facts:{...FIRST_ROUTE_FACTS,housing_basis:'guest'},confirm:true}),true);
  assert.equal(isCaseIntakePayload({facts:{...FIRST_ROUTE_FACTS},confirm:'true'}),false);
  assert.equal(isCaseIntakePayload({facts:{...FIRST_ROUTE_FACTS},confirm:true,secret:'x'}),false);
});

test('case facts are an explicit product-route filter, not an eligibility result',()=>{
  assert.equal(firstRouteIntakeState({},false),'incomplete');
  assert.equal(firstRouteIntakeState(FIRST_ROUTE_FACTS,false),'needs_confirmation');
  assert.equal(firstRouteIntakeState(FIRST_ROUTE_FACTS,true),'confirmed');
  assert.equal(firstRouteIntakeState({...FIRST_ROUTE_FACTS,housing_basis:'guest'},true),'outside_first_scenario');
});
