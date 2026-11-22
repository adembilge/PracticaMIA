import 'server-only';
import {NextRequest,NextResponse} from 'next/server';
import {headers as requestHeaders} from 'next/headers';
import {auth0} from '@/lib/auth0';
import {backendOrigin,sameOrigin} from '@/lib/auth-configuration.js';

const privateHeaders={'Cache-Control':'private, no-store'};
type Method='GET'|'POST'|'PUT'|'PATCH'|'DELETE';

async function previewIdentity(backend:string):Promise<string|null>{
  if(process.env.VERCEL_ENV!=='preview'||
    backend!=='https://practicamia-api-git-preview-auth-rev-599637-firatadembilge-4729.vercel.app')return null;
  const oidc=(await requestHeaders()).get('x-vercel-oidc-token');
  if(!oidc)throw new Error('Preview service identity unavailable');
  return oidc;
}

export function backendError(message:string,status:number){
  return NextResponse.json({error:message},{status,headers:privateHeaders});
}

export function rejectCrossOrigin(request:NextRequest){
  return sameOrigin(request.url,request.headers.get('origin'))
    ? null : backendError('Forbidden origin',403);
}

export async function proxyAuthenticatedRequest(method:Method,path:string,payload?:unknown,timeoutMs=8000){
  if(!auth0)return backendError('Service not configured',503);
  const backend=backendOrigin(process.env.BACKEND_API_URL,process.env.NODE_ENV);
  if(!backend)return backendError('Service not configured',503);
  try{
    const session=await auth0.getSession();
    if(!session)return backendError('Authentication required',401);
    let token:string;
    try{
      const credential=await auth0.getAccessToken();
      if(!credential.token)return backendError('Authentication needs renewal',401);
      token=credential.token;
    }catch{return backendError('Authentication needs renewal',401);}
    const oidc=await previewIdentity(backend);
    const response=await fetch(backend+path,{
      method,
      headers:{
        Authorization:'Bearer '+token,
        ...(oidc?{'x-vercel-trusted-oidc-idp-token':oidc}:{}),
        ...(payload!==undefined?{'Content-Type':'application/json'}:{}),
      },
      ...(payload!==undefined?{body:JSON.stringify(payload)}:{}),
      redirect:'manual',cache:'no-store',signal:AbortSignal.timeout(timeoutMs),
    });
    return new NextResponse(response.status===204?null:await response.text(),{
      status:response.status,headers:{...privateHeaders,'Content-Type':'application/json'},
    });
  }catch{return backendError('Backend unavailable',502);}
}
