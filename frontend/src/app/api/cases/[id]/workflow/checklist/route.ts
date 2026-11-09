import {NextRequest} from 'next/server';
import {isCaseId} from '@/lib/case-scope.js';
import {caseError,proxyCaseRequest,rejectCrossOrigin} from '@/lib/case-proxy';
import {validReviewMark} from '@/lib/case-workflow.js';

export const dynamic='force-dynamic';
type Context={params:Promise<{id:string}>};

export async function PATCH(request:NextRequest,{params}:Context){
  const originError=rejectCrossOrigin(request);
  if(originError)return originError;
  const {id}=await params;
  if(!isCaseId(id))return caseError('Case not found',404);
  if(!request.headers.get('content-type')?.startsWith('application/json'))
    return caseError('Unsupported content type',415);
  const length=Number(request.headers.get('content-length')||'0');
  if(!Number.isSafeInteger(length)||length<1||length>300)
    return caseError('Invalid request size',413);
  const payload:unknown=await request.json().catch(()=>null);
  if(!validReviewMark(payload))return caseError('Invalid review mark',422);
  return proxyCaseRequest('PATCH',
    '/api/v1/cases/'+id+'/workflow/checklist',payload,20000);
}
