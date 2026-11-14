import {NextRequest} from 'next/server';
import {isCaseId} from '@/lib/case-scope.js';
import {caseError,proxyCaseRequest,rejectCrossOrigin} from '@/lib/case-proxy';
import {privateDocumentsUiEnabled} from '@/lib/private-documents.js';

export const dynamic='force-dynamic';
type Context={params:Promise<{id:string;documentId:string}>};

export async function POST(request:NextRequest,{params}:Context){
  if(!privateDocumentsUiEnabled(process.env))return caseError('Not found',404);
  const crossOrigin=rejectCrossOrigin(request);
  if(crossOrigin)return crossOrigin;
  const {id,documentId}=await params;
  if(!isCaseId(id)||!isCaseId(documentId))return caseError('Not found',404);
  return proxyCaseRequest('POST',
    '/api/v1/cases/'+id+'/private-documents/'+documentId+'/intelligence/extract');
}
