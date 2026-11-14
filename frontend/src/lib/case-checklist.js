/** Presentation-only validation. The backend independently rechecks the
 * signed catalog and original approved source snapshots on each request.
 */
import {FIRST_ROUTE_SOURCE_LINKS} from './approved-source-view.js';

export const FIRST_ROUTE_VERSION_IDS = Object.freeze({
  'milano-italian-residence-change':'e139e910-3a89-4994-b450-b5107d8db7dd',
  'anpr-public-docs-residence-guide':'c89b4c40-4c41-48d5-ad52-be08e9630277',
});
export const SIGNED_ACTION_IDS = Object.freeze([
  'italian_change_anpr_guidance',
  'italian_change_tari_followup',
  'registered_rental_anpr_fields',
  'tenant_attachments_reference_only',
  'applicant_only_anpr_handoff',
]);

export function verifiedChecklistEvidence(e) {
  if(!e||typeof e!=='object'||Array.isArray(e))return false;
  const pinned=FIRST_ROUTE_SOURCE_LINKS[e.source_id];
  const version=FIRST_ROUTE_VERSION_IDS[e.source_id];
  return Boolean(pinned&&version&&
    e.official_url===pinned.url &&
    e.source_version_id===version &&
    typeof e.citation_id==='string'&&
    e.citation_id.startsWith(version+':') &&
    /^\d{4}-\d{2}-\d{2}T/.test(e.reviewed_at||'') &&
    e.archived_reference===(e.source_id==='anpr-public-docs-residence-guide'));
}

export function validateCaseChecklist(v) {
  if(!v||typeof v!=='object'||Array.isArray(v)||
      typeof v.status!=='string'||typeof v.next_action!=='string'||
      !Array.isArray(v.items)||v.synthetic_only!==true||
      v.first_scenario_only!==true||
      v.eligibility_evaluated!==false||v.documents_verified!==false||
      v.government_submitted!==false)return false;
  if(v.status==='ready_for_user_review'){
    if(v.verified_evidence!==true||
       v.ruleset_version!=='milan_italian_individual_registered_rental_v1_20261108'||
       !Array.isArray(v.required_document_types)||v.required_document_types.length||
       v.items.length!==5)return false;
    const ids=new Set();
    return v.items.every(i=>{
      if(!i||!SIGNED_ACTION_IDS.includes(i.id)||ids.has(i.id)||
         typeof i.description!=='string'||i.description.length>300||
         i.status!=='needs_user'||i.obligation_class!=='reviewed_action'||
         !Array.isArray(i.evidence)||i.evidence.length===0||
         !i.evidence.every(verifiedChecklistEvidence))return false;
      ids.add(i.id);
      return true;
    });
  }
  return ['needs_scope','needs_confirmation','outside_first_route','evidence_unavailable']
    .includes(v.status)&&v.items.length===0&&v.verified_evidence===false;
}
