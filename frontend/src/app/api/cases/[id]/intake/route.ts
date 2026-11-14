import { NextRequest } from 'next/server';
import { isCaseId } from '@/lib/case-scope.js';
import { caseError, proxyCaseRequest, rejectCrossOrigin } from '@/lib/case-proxy';
import { isCaseIntakePayload } from '@/lib/case-intake.js';

export const dynamic = 'force-dynamic';
type Context = {params: Promise<{id:string}>};

export async function GET(_req: NextRequest,{params}:Context) {
  const {id}=await params;
  if(!isCaseId(id)) return caseError('Case not found',404);
  return proxyCaseRequest('GET','/api/v1/cases/'+id+'/intake');
}

export async function PUT(req: NextRequest,{params}:Context) {
  const originError=rejectCrossOrigin(req);
  if(originError) return originError;
  const {id}=await params;
  if(!isCaseId(id)) return caseError('Case not found',404);
  if(!req.headers.get('content-type')?.startsWith('application/json')) {
    return caseError('Invalid content type',415);
  }
  const size=Number(req.headers.get('content-length')||'0');
  if(!Number.isSafeInteger(size)||size<1||size>2048) {
    return caseError('Request too large or missing length',413);
  }
  const raw:unknown=await req.json().catch(()=>null);
  if(!isCaseIntakePayload(raw)) return caseError('Invalid intake payload',422);
  return proxyCaseRequest('PUT','/api/v1/cases/'+id+'/intake',raw);
}

export async function DELETE(req: NextRequest,{params}:Context) {
  const originError=rejectCrossOrigin(req);
  if(originError) return originError;
  const {id}=await params;
  if(!isCaseId(id)) return caseError('Case not found',404);
  return proxyCaseRequest('DELETE','/api/v1/cases/'+id+'/intake');
}
