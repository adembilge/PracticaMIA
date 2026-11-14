import {NextRequest} from 'next/server';
import {isCaseId} from '@/lib/case-scope.js';
import {caseError,proxyCaseRequest} from '@/lib/case-proxy';
import {privateDocumentsUiEnabled} from '@/lib/private-documents.js';

export const dynamic='force-dynamic';
type Context={params:Promise<{id:string;documentId:string}>};

export async function GET(_request:NextRequest,{params}:Context){
  if(!privateDocumentsUiEnabled(process.env))return caseError('Not found',404);
  const {id,documentId}=await params;
  if(!isCaseId(id)||!isCaseId(documentId))return caseError('Not found',404);
  return proxyCaseRequest('GET',
    '/api/v1/cases/'+id+'/private-documents/'+documentId+'/intelligence');
}
