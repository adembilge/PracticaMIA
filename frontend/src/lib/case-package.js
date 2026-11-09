/** Backend remains authoritative; this validates the bounded package shape
 * before the browser advertises a downloadable preparation draft.
 */
import {FIRST_ROUTE_VERSION_IDS,SIGNED_ACTION_IDS,verifiedChecklistEvidence}
  from './case-checklist.js';

export const PREPARATION_ISSUES = Object.freeze({
  checklist_needs_scope:'Initial scope answers are incomplete',
  checklist_needs_confirmation:'Case intake has not been confirmed',
  checklist_outside_first_route:'This example is outside the supported route',
  checklist_evidence_unavailable:'A signed rule or official citation is unavailable',
  intake_not_confirmed:'Intake is not confirmed',
  intake_data_invalid:'Saved intake could not be verified',
  private_document_processing_not_enabled:'Secure document review is not enabled',
  document_review_unavailable:'Document review is temporarily unavailable',
  no_documents_reviewed:'No private documents have been reviewed',
  document_needs_extraction:'Document extraction is outstanding',
  document_needs_user_confirmation:'Document review is not confirmed',
  document_conflict:'Document and case facts conflict',
  document_comparison_unresolved:'Some document comparisons are unresolved',
  document_needs_manual_review:'Document review needs manual attention',
  document_unreadable:'An uploaded document is unreadable',
  document_no_supported_fields:'No supported document fields were found',
  document_needs_confirmed_intake:'Document comparison needs confirmed intake',
  document_needs_case_information:'Reviewed document field needs matching case information',
  document_unsupported_category:'Uploaded category is not automatically reviewed; draft stays non-official',
  document_limit_exceeded:'Document count needs investigation',
  unscanned_document:'An uploaded document has no scan record',
  unrecognized_document_review:'Document review could not be verified',
});
export const REQUIRED_PACKAGE_FACTS = Object.freeze([
  'citizenship_class','registration_context','destination_municipality',
  'household_scope','housing_basis',
]);

export function validPackageManifest(x) {
  if(!x||typeof x!=='object'||Array.isArray(x)||
     !['reviewable_draft','blocked'].includes(x.status)||
     typeof x.download_allowed!=='boolean'||
     x.draft_only!==true||x.synthetic_only!==true||
     x.eligibility_evaluated!==false||
     x.document_requirements_verified!==false||
     x.documents_legally_verified!==false||
     x.official_submission!==false||x.official_acceptance!==false||
     !/^[a-f0-9]{8}$/i.test(x.case_reference||'')||
     x.procedure_id!=='milan_residence_change'||
     x.jurisdiction!=='IT-MI-MILANO'||
     !Array.isArray(x.checklist)||!Array.isArray(x.confirmed_facts)||
     !Array.isArray(x.documents)||!Array.isArray(x.outstanding_issues)||
     x.documents.length>5||x.outstanding_issues.length>18||
     !x.official_handoff ||
     x.official_handoff.anpr_portal!=='https://www.anagrafenazionale.interno.it/'||
     x.official_handoff.milan_service!==
       'https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza')return false;
  if(!x.outstanding_issues.every(k=>typeof k==='string'&&
     Object.hasOwn(PREPARATION_ISSUES,k)))return false;
  if(!x.documents.every(d=>d&&Number.isInteger(d.number)&&d.number>=1&&d.number<=5&&
      ['housing_document','identity_document','other_supporting_document'].includes(d.category)&&
      typeof d.review_status==='string'&&d.review_status.length<=40&&
      Array.isArray(d.comparisons)&&d.comparisons.length<=2&&
      d.comparisons.every(c=>['housing_basis','move_in_date'].includes(c.field)&&
        ['match','conflict','no_confirmed_case_fact'].includes(c.result))))return false;
  if(x.status==='blocked')
    return !x.download_allowed&&x.outstanding_issues.length>0;
  if(!x.download_allowed||
     x.reviewed_ruleset!=='milan_italian_individual_registered_rental_v1_20261108'||
     x.confirmed_facts.length<5||x.confirmed_facts.length>6||
     x.checklist.length!==5)return false;
  const fields=x.confirmed_facts.map(f=>f?.field);
  if(new Set(fields).size!==fields.length||
     !REQUIRED_PACKAGE_FACTS.every(f=>fields.includes(f))||
     !x.confirmed_facts.every(f=>typeof f.value==='string'&&
       f.value.length>0&&f.value.length<=40&&
       typeof f.label==='string'&&f.label.length<=90&&
       f.provenance==='user_confirmed'))return false;
  const ids=new Set();
  return x.checklist.every(item=>{
    if(!item||!SIGNED_ACTION_IDS.includes(item.id)||ids.has(item.id)||
       item.status!=='needs_user'||typeof item.description!=='string'||
       item.description.length>300||!Array.isArray(item.evidence)||
       item.evidence.length===0||!item.evidence.every(verifiedChecklistEvidence))return false;
    ids.add(item.id);return true;
  });
}
