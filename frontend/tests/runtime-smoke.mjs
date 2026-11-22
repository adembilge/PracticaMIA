/** Production-mode HTTP smoke tests for the single-chat product shell. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {setTimeout as sleep} from 'node:timers/promises';
import {createServer} from 'node:net';
import {once} from 'node:events';

async function freePort(){
  const server=createServer();
  server.listen(0,'127.0.0.1');
  await once(server,'listening');
  const port=server.address().port;
  await new Promise(resolve=>server.close(resolve));
  return port;
}

async function withServer(overrides,fn){
  const port=await freePort();
  const origin='http://127.0.0.1:'+port;
  const child=spawn(process.execPath,['node_modules/next/dist/bin/next','start','-p',String(port),'-H','127.0.0.1'],{
    cwd:process.cwd(),
    env:{...process.env,NODE_ENV:'production',VERCEL_ENV:'production',
      AUTH0_DOMAIN:'',AUTH0_CLIENT_ID:'',AUTH0_CLIENT_SECRET:'',AUTH0_SECRET:'',
      AUTH0_AUDIENCE:'',BACKEND_API_URL:'',...overrides},
    stdio:['ignore','pipe','pipe'],
  });
  let output='';
  for(const stream of [child.stdout,child.stderr]) stream.on('data',chunk=>{output=(output+chunk.toString()).slice(-5000)});
  try{
    let started=false;
    for(let n=0;n<100;n++){
      if(child.exitCode!==null)break;
      try{const response=await fetch(origin+'/',{signal:AbortSignal.timeout(1200)});if(response.status===200){started=true;break;}}catch{}
      await sleep(180);
    }
    assert.equal(started,true,'Next.js failed to start: '+output);
    return await fn(origin);
  }finally{
    if(child.exitCode===null){
      const stopped=once(child,'exit').catch(()=>null);
      child.kill('SIGTERM');
      await Promise.race([stopped,sleep(2500)]);
      if(child.exitCode===null)child.kill('SIGKILL');
    }
  }
}

test('production HTTP serves one chat and removes legacy customer routes', {timeout:45000},async()=>{
  await withServer({},async origin=>{
    const root=await fetch(origin+'/');
    assert.equal(root.status,200);
    const html=await root.text();
    assert.match(html,/How can I help\?/);
    assert.match(html,/Message PracticaMIA/);
    assert.doesNotMatch(html,/Prepare my case|Explore a fictional case|Saved cases|INTERACTIVE PROTOTYPE|Preview/);
    for(const pathname of ['/cases/new','/cases/saved','/cases/demo','/demo/synthetic','/account']){
      const response=await fetch(origin+pathname);
      assert.equal(response.status,404,pathname);
    }
    for(const pathname of ['/api/cases','/api/demo/ai','/api/agent/conversations']){
      const response=await fetch(origin+pathname);
      assert.equal(response.status,404,pathname);
    }
    const reviewer=await fetch(origin+'/knowledge/review');
    assert.equal(reviewer.status,404);
    const response=await fetch(origin+'/api/conversations/tasks/00000000-0000-0000-0000-000000000001/intake');
    assert.equal(response.status,503,'internal task endpoint must fail closed without Auth0');
  });
});
