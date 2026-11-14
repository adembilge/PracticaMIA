import assert from 'node:assert/strict';
import test from 'node:test';
import {FIRST_ROUTE_SOURCE_LINKS, selectReviewedFirstRouteSources} from '../src/lib/approved-source-view.js';

const source=(id) => ({
  source_id:id,source_version_id:'version-1',title:'Reviewed public reference',
  official_url:FIRST_ROUTE_SOURCE_LINKS[id].url,
  reviewed_at:'2026-11-07T23:50:57Z',
  procedure_id:'milan_residence_change',
  jurisdiction:'IT-MI-MILANO',content_sha256:'a'.repeat(64),
});

test('only precisely allowlisted reviewed first-route sources are displayed', () => {
 const valid=[source('milano-italian-residence-change'),source('anpr-public-docs-residence-guide')];
 assert.equal(selectReviewedFirstRouteSources({status:'approved_sources_available',sources:valid}).length,2);
 assert.equal(selectReviewedFirstRouteSources({status:'insufficient_evidence',sources:valid}).length,0);
});

test('untrusted URLs, duplicate sources and mismatched integrity identifiers fail closed', () => {
 const original=source('milano-italian-residence-change');
 assert.equal(selectReviewedFirstRouteSources({status:'approved_sources_available',sources:[
  {...original,official_url:'https://attacker.example'},
  {...original,content_sha256:'short'},
  original,original,
 ]}).length,1);
 assert.equal(selectReviewedFirstRouteSources({status:'approved_sources_available',sources:[
   {...original,source_id:'milano-foreign-rental-documents'},
 ]}).length,0);
});
