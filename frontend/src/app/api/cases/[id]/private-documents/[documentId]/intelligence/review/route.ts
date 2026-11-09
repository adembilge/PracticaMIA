import {NextRequest} from 'next/server';
import {isCaseId} from '@/lib/case-scope.js';
import {caseError,proxyCaseRequest,rejectCrossOrigin} from '@/lib/case-proxy';
import {privateDocumentsUiEnabled} from '@/lib/private-documents.js';
import {validateIntelligenceReview} from '@/lib/private-document-intelligence.js';

export const dynamic='force-dynamic';
type Context={params:Promise<{id:string;documentId:string}>};

export async function PUT(request:NextRequest,{params}:Context){
  if(!privateDocumentsUiEnabled(process.env))return caseError('Not found',404);
  const crossOrigin=rejectCrossOrigin(request);
  if(crossOrigin)return crossOrigin;
  const {id,documentId}=await params;
  if(!isCaseId(id)||!isCaseId(documentId))return caseError('Not found',404);
  if(!request.headers.get('content-type')?.startsWith('application/json'))
    return caseError('Unsupported content type',415);
  const length=Number(request.headers.get('content-length')||'0');
  if(!Number.isSafeInteger(length)||length<1||length>2048)
    return caseError('Invalid request size',413);
  const data:unknown=await request.json().catch(()=>null);
  if(!validateIntelligenceReview(data))return caseError('Invalid review',422);
  return proxyCaseRequest('PUT',
    '/api/v1/cases/'+id+'/private-documents/'+documentId+'/intelligence/review',data);
}
