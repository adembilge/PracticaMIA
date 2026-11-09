/** Explicit review of bounded source-backed housing/date candidates only.
 * Client validation complements, never replaces, backend validation.
 */
export const INTAKE_DOCUMENT_FIELDS = Object.freeze(['housing_basis','move_in_date']);
export const INTAKE_HOUSING_VALUES = Object.freeze([
  'registered_private_rental','owner','guest','other'
]);
export function isDateOnly(value){
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
  const [y,m,d]=value.split('-').map(Number);
  const normalized=new Date(Date.UTC(y,m-1,d));
  return y>=1900&&y<=2100&&normalized.getUTCFullYear()===y&&
    normalized.getUTCMonth()===m-1&&normalized.getUTCDate()===d;
}
export function isReviewedValue(field,value){
  return typeof value==='string'&&(
    field==='housing_basis'?INTAKE_HOUSING_VALUES.includes(value):
      field==='move_in_date'&&isDateOnly(value)
  );
}
export function validateIntelligenceReview(value){
  if(!value||typeof value!=='object'||Array.isArray(value)||
    Object.keys(value).sort().join(',')!=='confirm,extraction_digest,selections'||
    value.confirm!==true||
    typeof value.extraction_digest!=='string'||
    !/^[0-9a-f]{64}$/.test(value.extraction_digest)||
    !Array.isArray(value.selections)||value.selections.length<1||
    value.selections.length>2)return false;
  const fields=new Set();
  return value.selections.every(s=>{
    if(!s||typeof s!=='object'||Array.isArray(s)||
       Object.keys(s).sort().join(',')!=='candidate_id,confirmed_value,field_name'||
       !INTAKE_DOCUMENT_FIELDS.includes(s.field_name)||
       typeof s.candidate_id!=='string'||!/^[0-9a-f]{64}$/.test(s.candidate_id)||
       !isReviewedValue(s.field_name,s.confirmed_value)||
       fields.has(s.field_name))return false;
    fields.add(s.field_name);
    return true;
  });
}
export function validIntelligenceResponse(value){
  if(!value||typeof value!=='object'||Array.isArray(value)||
    !['needs_extraction','needs_user_confirmation','no_supported_fields',
      'unreadable','unsupported_category','conflict','needs_manual_review',
      'needs_confirmed_intake','needs_case_information',
      'user_reviewed_unverified'].includes(value.status)||
    value.no_legal_verification!==true||value.official_submission!==false||
    !Array.isArray(value.candidates)||value.candidates.length>8||
    !Array.isArray(value.comparisons)||value.comparisons.length>2||
    !Array.isArray(value.ambiguous_fields)||typeof value.user_reviewed!=='boolean')return false;
  return value.candidates.every(c=>c&&typeof c==='object'&&
    INTAKE_DOCUMENT_FIELDS.includes(c.field_name)&&
    /^[0-9a-f]{64}$/.test(c.candidate_id||'')&&
    isReviewedValue(c.field_name,c.suggested_value)&&
    typeof c.raw_value==='string'&&c.raw_value.length<=100&&
    Number.isInteger(c.page)&&c.page>=1&&c.page<=15)&&
    value.comparisons.every(c=>c&&INTAKE_DOCUMENT_FIELDS.includes(c.field_name)&&
      isReviewedValue(c.field_name,c.reviewed_value)&&
      (c.case_value===null||isReviewedValue(c.field_name,c.case_value))&&
      ['match','conflict','no_confirmed_case_fact'].includes(c.comparison));
}
