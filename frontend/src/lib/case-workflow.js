/** Client-only validation for the single authenticated case workflow.
 * The server separately rebuilds signed rules, source approvals, and ownership.
 */
import {SIGNED_ACTION_IDS,verifiedChecklistEvidence} from './case-checklist.js';
import {PREPARATION_ISSUES} from './case-package.js';

export const WORKFLOW_STEPS=Object.freeze([
  'scope','intake','guidance','checklist','documents','package','handoff',
]);
export const WORKFLOW_ACTIONS=Object.freeze([
  'answer_scope','confirm_intake','consult_official','review_sources',
  'review_checklist','resolve_documents','download_draft','review_package',
]);
const STATUSES=new Set([
  'complete','blocked','needs_attention','locked','informational',
  'reviewed_by_user','unavailable','user_reviewed_unverified',
  'optional_unverified','draft_available','user_only_not_submitted',
]);

export function validReviewMark(value){
  return !!value&&typeof value==='object'&&!Array.isArray(value)&&
    Object.keys(value).sort().join(',')==='fingerprint,item_id,reviewed'&&
    SIGNED_ACTION_IDS.includes(value.item_id)&&
    typeof value.reviewed==='boolean'&&
    typeof value.fingerprint==='string'&&
    /^[0-9a-f]{64}$/.test(value.fingerprint);
}

export function validCaseWorkflow(value){
  if(!value||typeof value!=='object'||Array.isArray(value)||
     value.workflow_version!=='case-journey-v1'||
     value.synthetic_only!==true||value.official_submission!==false||
     value.eligibility_evaluated!==false||
     !/^[0-9a-f]{8}$/i.test(value.case_reference||'')||
     !WORKFLOW_ACTIONS.includes(value.next_action)||
     !Array.isArray(value.steps)||value.steps.length!==WORKFLOW_STEPS.length||
     !value.steps.every((s,i)=>s&&s.id===WORKFLOW_STEPS[i]&&STATUSES.has(s.status)))
    return false;
  const c=value.checklist,p=value.package,d=value.documents;
  if(!c||!p||!d||!['ready_for_user_review','unavailable'].includes(c.status)||
     !Array.isArray(c.items)||!Number.isInteger(c.reviewed_count)||
     !Number.isInteger(c.total)||c.reviewed_count<0||c.reviewed_count>5||
     !c.reviewed_items||typeof c.reviewed_items!=='object'||
     !['reviewable_draft','blocked'].includes(p.status)||
     typeof p.download_allowed!=='boolean'||
     !Array.isArray(p.outstanding_issues)||
     !p.outstanding_issues.every(x=>Object.hasOwn(PREPARATION_ISSUES,x))||
     typeof d.enabled!=='boolean'||d.legal_verification!==false||
     !Number.isInteger(d.reviewed_count)||!Number.isInteger(d.uploaded_count))
    return false;
  if(p.download_allowed !== (p.status==='reviewable_draft'))return false;
  if(c.status==='unavailable')
    return c.total===0&&c.items.length===0&&c.reviewed_count===0&&
      c.fingerprint===null&&Object.keys(c.reviewed_items).length===0;
  if(c.items.length!==5||c.total!==5||
     c.ruleset_version!=='milan_italian_individual_registered_rental_v1_20261108'||
     typeof c.fingerprint!=='string'||!/^[a-f0-9]{64}$/.test(c.fingerprint))
    return false;
  const seen=new Set();
  if(!c.items.every(item=>{
    if(!item||!SIGNED_ACTION_IDS.includes(item.id)||seen.has(item.id)||
       item.status!=='needs_user'||typeof item.description!=='string'||
       item.description.length>300||!Array.isArray(item.evidence)||
       !item.evidence.length||!item.evidence.every(verifiedChecklistEvidence))return false;
    seen.add(item.id);
    return true;
  }))return false;
  const reviewedIds=Object.keys(c.reviewed_items);
  return reviewedIds.length===c.reviewed_count&&
    reviewedIds.every(id=>seen.has(id)&&typeof c.reviewed_items[id]==='string'&&
      /^\d{4}-\d{2}-\d{2}T/.test(c.reviewed_items[id]));
}
