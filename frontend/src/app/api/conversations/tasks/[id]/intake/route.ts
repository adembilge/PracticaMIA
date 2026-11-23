import {NextRequest} from 'next/server';
import {isTaskId} from '@/lib/task-scope.js';
import {backendError,proxyAuthenticatedRequest,rejectCrossOrigin} from '@/lib/backend-proxy';
import {isRequestIntakePayload} from '@/lib/request-intake.js';

export const dynamic='force-dynamic';
type Context={params:Promise<{id:string}>};

export async function GET(_request:NextRequest,{params}:Context){
  const {id}=await params;
  if(!isTaskId(id))return backendError('Request not found',404);
  return proxyAuthenticatedRequest('GET','/api/v1/conversations/tasks/'+id+'/intake');
}
export async function PUT(request:NextRequest,{params}:Context){
  const originError=rejectCrossOrigin(request);
  if(originError)return originError;
  const {id}=await params;
  if(!isTaskId(id))return backendError('Request not found',404);
  if(!request.headers.get('content-type')?.startsWith('application/json'))
    return backendError('Invalid content type',415);
  const size=Number(request.headers.get('content-length')||'0');
  if(!Number.isSafeInteger(size)||size<1||size>2048)
    return backendError('Request too large or missing length',413);
  const raw:unknown=await request.json().catch(()=>null);
  if(!isRequestIntakePayload(raw))return backendError('Invalid request details',422);
  return proxyAuthenticatedRequest('PUT','/api/v1/conversations/tasks/'+id+'/intake',raw);
}
export async function DELETE(request:NextRequest,{params}:Context){
  const originError=rejectCrossOrigin(request);
  if(originError)return originError;
  const {id}=await params;
  if(!isTaskId(id))return backendError('Request not found',404);
  return proxyAuthenticatedRequest('DELETE','/api/v1/conversations/tasks/'+id+'/intake');
}
